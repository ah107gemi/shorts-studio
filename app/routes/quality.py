"""
Quality check routes for Shorts Studio.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Project, Scene, Script
from app.schemas import QualityCheckItem, QualityReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _run_checks(project: Project, db: Session) -> list[QualityCheckItem]:
    """Execute all quality checks and return results."""
    checks: list[QualityCheckItem] = []
    project_id = project.id

    # 1. Has at least one approved script
    approved_scripts = (
        db.query(func.count(Script.id))
        .filter(Script.project_id == project_id, Script.is_approved == True)
        .scalar() or 0
    )
    if approved_scripts > 0:
        checks.append(QualityCheckItem(
            check_name="approved_script",
            status="pass",
            message="Project has an approved script",
            details={"count": approved_scripts},
        ))
    else:
        total_scripts = (
            db.query(func.count(Script.id))
            .filter(Script.project_id == project_id)
            .scalar() or 0
        )
        checks.append(QualityCheckItem(
            check_name="approved_script",
            status="fail" if total_scripts == 0 else "warning",
            message="No approved script" if total_scripts == 0 else "Script exists but not approved",
            details={"total_scripts": total_scripts},
        ))

    # 2. Has scenes
    scene_count = (
        db.query(func.count(Scene.id))
        .filter(Scene.project_id == project_id)
        .scalar() or 0
    )
    if scene_count > 0:
        checks.append(QualityCheckItem(
            check_name="has_scenes",
            status="pass",
            message=f"Project has {scene_count} scene(s)",
            details={"count": scene_count},
        ))
    else:
        checks.append(QualityCheckItem(
            check_name="has_scenes",
            status="fail",
            message="No scenes defined",
        ))

    # 3. Total duration within target
    total_duration = (
        db.query(func.sum(Scene.duration_seconds))
        .filter(Scene.project_id == project_id)
        .scalar() or 0.0
    )
    target = project.target_duration_seconds
    if total_duration == 0:
        checks.append(QualityCheckItem(
            check_name="duration",
            status="fail",
            message="Total scene duration is 0",
            details={"total": 0, "target": target},
        ))
    elif abs(total_duration - target) <= target * 0.2:
        checks.append(QualityCheckItem(
            check_name="duration",
            status="pass",
            message=f"Duration ({total_duration:.1f}s) is within 20% of target ({target}s)",
            details={"total": round(total_duration, 2), "target": target},
        ))
    else:
        checks.append(QualityCheckItem(
            check_name="duration",
            status="warning",
            message=f"Duration ({total_duration:.1f}s) deviates from target ({target}s)",
            details={"total": round(total_duration, 2), "target": target},
        ))

    # 4. Scenes have visual assets
    scenes_without_visual = (
        db.query(func.count(Scene.id))
        .filter(Scene.project_id == project_id, Scene.asset_id == None)
        .scalar() or 0
    )
    if scene_count > 0 and scenes_without_visual == 0:
        checks.append(QualityCheckItem(
            check_name="visual_assets",
            status="pass",
            message="All scenes have visual assets assigned",
        ))
    elif scene_count > 0:
        checks.append(QualityCheckItem(
            check_name="visual_assets",
            status="warning",
            message=f"{scenes_without_visual}/{scene_count} scene(s) missing visual assets",
            details={"missing": scenes_without_visual, "total": scene_count},
        ))

    # 5. Scenes have narration text
    scenes_without_narration = (
        db.query(func.count(Scene.id))
        .filter(
            Scene.project_id == project_id,
            (Scene.narration_text == None) | (Scene.narration_text == ""),
        )
        .scalar() or 0
    )
    if scene_count > 0 and scenes_without_narration == 0:
        checks.append(QualityCheckItem(
            check_name="narration",
            status="pass",
            message="All scenes have narration text",
        ))
    elif scene_count > 0:
        checks.append(QualityCheckItem(
            check_name="narration",
            status="warning",
            message=f"{scenes_without_narration}/{scene_count} scene(s) missing narration",
            details={"missing": scenes_without_narration, "total": scene_count},
        ))

    # 6. Resolution check
    if project.resolution_w >= 1080 and project.resolution_h >= 1920:
        checks.append(QualityCheckItem(
            check_name="resolution",
            status="pass",
            message=f"Resolution {project.resolution_w}x{project.resolution_h} meets minimum",
        ))
    else:
        checks.append(QualityCheckItem(
            check_name="resolution",
            status="warning",
            message=f"Resolution {project.resolution_w}x{project.resolution_h} is below recommended 1080x1920",
        ))

    return checks


@router.post("/projects/{project_id}/quality-check", response_model=QualityReportResponse)
def run_quality_check(project_id: str, db: Session = Depends(get_db)):
    """Run quality checks on a project and return the report."""
    project = _ensure_project(project_id, db)
    checks = _run_checks(project, db)

    # Determine overall status
    statuses = [c.status for c in checks]
    if "fail" in statuses:
        overall = "fail"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "pass"

    # Score: pass=1, warning=0.5, fail=0
    score_map = {"pass": 1.0, "warning": 0.5, "fail": 0.0}
    total_score = sum(score_map.get(s, 0) for s in statuses)
    score = round((total_score / len(checks)) * 100, 1) if checks else 0.0

    return QualityReportResponse(
        project_id=project_id,
        overall_status=overall,
        checks=checks,
        checked_at=datetime.utcnow(),
        score=score,
    )


@router.get("/projects/{project_id}/quality-report", response_model=QualityReportResponse)
def get_quality_report(project_id: str, db: Session = Depends(get_db)):
    """Get the latest quality report (re-runs checks on demand).

    In a future version this would return a cached report; for now it
    regenerates on every request for simplicity.
    """
    project = _ensure_project(project_id, db)
    checks = _run_checks(project, db)

    statuses = [c.status for c in checks]
    if "fail" in statuses:
        overall = "fail"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "pass"

    score_map = {"pass": 1.0, "warning": 0.5, "fail": 0.0}
    total_score = sum(score_map.get(s, 0) for s in statuses)
    score = round((total_score / len(checks)) * 100, 1) if checks else 0.0

    return QualityReportResponse(
        project_id=project_id,
        overall_status=overall,
        checks=checks,
        checked_at=datetime.utcnow(),
        score=score,
    )
