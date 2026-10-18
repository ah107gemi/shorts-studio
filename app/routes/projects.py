"""
Project CRUD routes for Shorts Studio.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Job, Project, Scene, Script
from app.schemas import (
    MessageResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Created project %s – %s", project.id[:8], project.name)
    return project


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    db: Session = Depends(get_db),
):
    """List all projects, optionally filtered by status."""
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    # Exclude archived by default unless explicitly requested
    if status != "archived":
        query = query.filter(Project.status != "archived")
    projects = query.order_by(Project.updated_at.desc()).all()
    return projects


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a single project with counts of related entities."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script_count = db.query(func.count(Script.id)).filter(Script.project_id == project_id).scalar() or 0
    scene_count = db.query(func.count(Scene.id)).filter(Scene.project_id == project_id).scalar() or 0
    asset_count = db.query(func.count(Asset.id)).filter(Asset.project_id == project_id).scalar() or 0

    response = ProjectDetailResponse.model_validate(project)
    response.script_count = script_count
    response.scene_count = scene_count
    response.asset_count = asset_count
    return response


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
):
    """Update project fields."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    logger.info("Updated project %s", project_id[:8])
    return project


@router.delete("/projects/{project_id}", response_model=MessageResponse)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Soft-delete a project by setting status to 'archived'."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "archived"
    db.commit()
    logger.info("Archived project %s", project_id[:8])
    return MessageResponse(message="Project archived", detail=project_id)


@router.post("/projects/{project_id}/duplicate", response_model=ProjectResponse, status_code=201)
def duplicate_project(project_id: str, db: Session = Depends(get_db)):
    """Duplicate a project (metadata only, not assets/renders)."""
    original = db.query(Project).filter(Project.id == project_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Project not found")

    new_project = Project(
        name=f"{original.name} (copy)",
        description=original.description,
        topic=original.topic,
        niche=original.niche,
        target_audience=original.target_audience,
        language=original.language,
        target_duration_seconds=original.target_duration_seconds,
        tone=original.tone,
        style=original.style,
        platform=original.platform,
        visual_style=original.visual_style,
        voice_preference=original.voice_preference,
        resolution_w=original.resolution_w,
        resolution_h=original.resolution_h,
        fps=original.fps,
        settings_json=original.settings_json,
    )
    db.add(new_project)

    # Duplicate scripts
    for script in original.scripts:
        new_script = Script(
            project_id=new_project.id,
            version=script.version,
            content=script.content,
            hook=script.hook,
            body=script.body,
            conclusion=script.conclusion,
            cta=script.cta,
            word_count=script.word_count,
            estimated_duration_seconds=script.estimated_duration_seconds,
            notes=script.notes,
        )
        db.add(new_script)

    db.commit()
    db.refresh(new_project)
    logger.info("Duplicated project %s → %s", project_id[:8], new_project.id[:8])
    return new_project


@router.get("/projects/{project_id}/stats", response_model=ProjectStatsResponse)
def get_project_stats(project_id: str, db: Session = Depends(get_db)):
    """Get project statistics."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script_count = db.query(func.count(Script.id)).filter(Script.project_id == project_id).scalar() or 0
    scene_count = db.query(func.count(Scene.id)).filter(Scene.project_id == project_id).scalar() or 0
    asset_count = db.query(func.count(Asset.id)).filter(Asset.project_id == project_id).scalar() or 0
    job_count = db.query(func.count(Job.id)).filter(Job.project_id == project_id).scalar() or 0
    completed_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.project_id == project_id, Job.status == "completed")
        .scalar() or 0
    )
    failed_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.project_id == project_id, Job.status == "failed")
        .scalar() or 0
    )
    total_duration = (
        db.query(func.sum(Scene.duration_seconds))
        .filter(Scene.project_id == project_id)
        .scalar() or 0.0
    )

    return ProjectStatsResponse(
        project_id=project_id,
        script_count=script_count,
        scene_count=scene_count,
        asset_count=asset_count,
        job_count=job_count,
        total_scene_duration=float(total_duration),
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
    )
