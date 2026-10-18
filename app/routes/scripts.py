"""
Script management routes for Shorts Studio.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Project, Script
from app.schemas import (
    JobResponse,
    MessageResponse,
    ScriptCreate,
    ScriptGenerateRequest,
    ScriptResponse,
    ScriptUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Average speaking rate used to estimate narration duration.
_WORDS_PER_MINUTE = 150.0


def _compute_word_count(script: Script) -> int:
    """Count words across all text fields of a script."""
    parts = [script.content, script.hook, script.body, script.conclusion, script.cta]
    total = 0
    for part in parts:
        if part:
            total += len(part.split())
    return total


def _estimate_duration(word_count: int) -> float:
    """Estimate narration duration in seconds from word count."""
    return round((word_count / _WORDS_PER_MINUTE) * 60, 2) if word_count else 0.0


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/scripts", response_model=ScriptResponse, status_code=201)
def create_script(project_id: str, payload: ScriptCreate, db: Session = Depends(get_db)):
    """Create a new script version for the project."""
    _ensure_project(project_id, db)

    # Determine next version number
    max_version = (
        db.query(func.max(Script.version))
        .filter(Script.project_id == project_id)
        .scalar() or 0
    )

    script = Script(
        project_id=project_id,
        version=max_version + 1,
        **payload.model_dump(),
    )
    script.word_count = _compute_word_count(script)
    script.estimated_duration_seconds = _estimate_duration(script.word_count)

    db.add(script)
    db.commit()
    db.refresh(script)
    logger.info("Created script v%d for project %s", script.version, project_id[:8])
    return script


@router.get("/projects/{project_id}/scripts", response_model=list[ScriptResponse])
def list_scripts(project_id: str, db: Session = Depends(get_db)):
    """List all script versions for a project."""
    _ensure_project(project_id, db)
    scripts = (
        db.query(Script)
        .filter(Script.project_id == project_id)
        .order_by(Script.version.desc())
        .all()
    )
    return scripts


@router.get("/projects/{project_id}/scripts/{script_id}", response_model=ScriptResponse)
def get_script(project_id: str, script_id: str, db: Session = Depends(get_db)):
    """Get a specific script."""
    script = (
        db.query(Script)
        .filter(Script.id == script_id, Script.project_id == project_id)
        .first()
    )
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/projects/{project_id}/scripts/{script_id}", response_model=ScriptResponse)
def update_script(
    project_id: str,
    script_id: str,
    payload: ScriptUpdate,
    db: Session = Depends(get_db),
):
    """Update script content."""
    script = (
        db.query(Script)
        .filter(Script.id == script_id, Script.project_id == project_id)
        .first()
    )
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(script, field, value)

    # Recalculate word count and duration
    script.word_count = _compute_word_count(script)
    script.estimated_duration_seconds = _estimate_duration(script.word_count)

    db.commit()
    db.refresh(script)
    logger.info("Updated script %s", script_id[:8])
    return script


@router.post(
    "/projects/{project_id}/scripts/{script_id}/approve",
    response_model=ScriptResponse,
)
def approve_script(project_id: str, script_id: str, db: Session = Depends(get_db)):
    """Mark a script as approved."""
    script = (
        db.query(Script)
        .filter(Script.id == script_id, Script.project_id == project_id)
        .first()
    )
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script.is_approved = True
    script.status = "approved"
    db.commit()
    db.refresh(script)
    logger.info("Approved script %s", script_id[:8])
    return script


@router.post("/projects/{project_id}/scripts/generate", response_model=JobResponse, status_code=202)
def generate_script(
    project_id: str,
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
):
    """Trigger AI script generation.  Creates a background Job and returns it."""
    project = _ensure_project(project_id, db)

    job = Job(
        project_id=project_id,
        job_type="script_generation",
        status="pending",
        current_stage="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Queued script generation job %s for project %s", job.id[:8], project_id[:8])
    return job
