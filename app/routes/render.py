"""
Render routes for Shorts Studio.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job, Project
from app.schemas import (
    RenderQueueItem,
    RenderQueueResponse,
    RenderStartRequest,
    RenderStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/render", response_model=RenderStatusResponse, status_code=202)
def start_render(
    project_id: str,
    payload: RenderStartRequest,
    db: Session = Depends(get_db),
):
    """Start a render job for the project."""
    project = _ensure_project(project_id, db)

    # Check for already-running render
    existing = (
        db.query(Job)
        .filter(
            Job.project_id == project_id,
            Job.job_type == "render",
            Job.status.in_(("pending", "queued", "running")),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A render job is already active (id={existing.id})",
        )

    render_settings = {
        "resolution_w": payload.resolution_w or project.resolution_w,
        "resolution_h": payload.resolution_h or project.resolution_h,
        "fps": payload.fps or project.fps,
        "quality": payload.quality,
        "output_format": payload.output_format,
    }

    job = Job(
        project_id=project_id,
        job_type="render",
        status="pending",
        current_stage="initializing",
        result_json=json.dumps(render_settings),
    )
    db.add(job)

    # Move project to rendering status
    project.status = "rendering"
    db.commit()
    db.refresh(job)

    logger.info("Started render job %s for project %s", job.id[:8], project_id[:8])
    return RenderStatusResponse(
        project_id=project_id,
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
    )


@router.get("/projects/{project_id}/render/status", response_model=RenderStatusResponse)
def get_render_status(project_id: str, db: Session = Depends(get_db)):
    """Get the latest render job status for a project."""
    _ensure_project(project_id, db)

    job = (
        db.query(Job)
        .filter(Job.project_id == project_id, Job.job_type == "render")
        .order_by(Job.created_at.desc())
        .first()
    )

    if not job:
        return RenderStatusResponse(
            project_id=project_id,
            status="no_render",
            progress=0.0,
        )

    output_path = None
    if job.result_json:
        try:
            result = json.loads(job.result_json)
            output_path = result.get("output_path")
        except (json.JSONDecodeError, TypeError):
            pass

    return RenderStatusResponse(
        project_id=project_id,
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        output_path=output_path,
        error_message=job.error_message,
    )


@router.get("/projects/{project_id}/render/preview", response_model=RenderStatusResponse)
def generate_preview(project_id: str, db: Session = Depends(get_db)):
    """Generate a low-resolution preview.

    Creates a render job with low quality preset.
    """
    project = _ensure_project(project_id, db)

    preview_settings = {
        "resolution_w": project.resolution_w // 2,
        "resolution_h": project.resolution_h // 2,
        "fps": min(project.fps, 15),
        "quality": "low",
        "output_format": "mp4",
        "is_preview": True,
    }

    job = Job(
        project_id=project_id,
        job_type="render",
        status="pending",
        current_stage="preview_init",
        result_json=json.dumps(preview_settings),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Queued preview render %s for project %s", job.id[:8], project_id[:8])
    return RenderStatusResponse(
        project_id=project_id,
        job_id=job.id,
        status=job.status,
        progress=0.0,
        current_stage=job.current_stage,
    )


@router.get("/render/queue", response_model=RenderQueueResponse)
def get_render_queue(db: Session = Depends(get_db)):
    """Get the global render queue status."""
    render_jobs = (
        db.query(Job)
        .filter(Job.job_type == "render")
        .order_by(Job.created_at.desc())
        .limit(50)
        .all()
    )

    items: list[RenderQueueItem] = []
    active_count = 0
    pending_count = 0

    for job in render_jobs:
        project = db.query(Project).filter(Project.id == job.project_id).first()
        project_name = project.name if project else "Unknown"

        items.append(RenderQueueItem(
            job_id=job.id,
            project_id=job.project_id,
            project_name=project_name,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
        ))

        if job.status == "running":
            active_count += 1
        elif job.status in ("pending", "queued"):
            pending_count += 1

    return RenderQueueResponse(
        queue=items,
        active_count=active_count,
        pending_count=pending_count,
    )
