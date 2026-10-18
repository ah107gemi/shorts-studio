"""
Job management routes for Shorts Studio.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Project
from app.schemas import JobResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Statuses considered "active"
_ACTIVE_STATUSES = ("pending", "queued", "running")


@router.get("/projects/{project_id}/jobs", response_model=list[JobResponse])
def list_project_jobs(project_id: str, db: Session = Depends(get_db)):
    """List all jobs for a project, newest first."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    jobs = (
        db.query(Job)
        .filter(Job.project_id == project_id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return jobs


@router.get("/jobs/active", response_model=list[JobResponse])
def list_active_jobs(db: Session = Depends(get_db)):
    """List all active (pending / queued / running) jobs across every project."""
    jobs = (
        db.query(Job)
        .filter(Job.status.in_(_ACTIVE_STATUSES))
        .order_by(Job.created_at.asc())
        .all()
    )
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a single job's status and progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a pending or running job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'",
        )

    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    logger.info("Cancelled job %s", job_id[:8])
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry a failed or cancelled job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job with status '{job.status}'",
        )

    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=400,
            detail=f"Job has reached maximum retries ({job.max_retries})",
        )

    job.status = "pending"
    job.progress = 0.0
    job.error_message = None
    job.current_stage = "queued (retry)"
    job.retry_count += 1
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)
    logger.info("Retrying job %s (attempt %d)", job_id[:8], job.retry_count)
    return job
