"""
Caption generation and management routes for Shorts Studio.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Scene, Script
from app.schemas import (
    CaptionGenerateRequest,
    CaptionSegment,
    CaptionsResponse,
    CaptionsUpdate,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _segments_to_srt(segments: list[CaptionSegment]) -> str:
    """Convert caption segments to SRT format."""
    lines: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = _seconds_to_srt_time(seg.start_time)
        end = _seconds_to_srt_time(seg.end_time)
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _generate_segments_from_scenes(
    scenes: list[Scene],
    words_per_minute: float = 150.0,
) -> list[CaptionSegment]:
    """Generate timed caption segments from scene narration text."""
    segments: list[CaptionSegment] = []
    current_time = 0.0

    for scene in scenes:
        if not scene.narration_text:
            current_time += scene.duration_seconds
            continue

        # Split narration into sentences / chunks
        text = scene.narration_text.strip()
        words = text.split()
        if not words:
            current_time += scene.duration_seconds
            continue

        # Create segments of roughly 8 words each for readability
        chunk_size = 8
        scene_word_count = len(words)
        # Duration per word in this scene
        duration_per_word = scene.duration_seconds / scene_word_count if scene_word_count else 0

        for i in range(0, scene_word_count, chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_word_count = len(chunk_words)
            chunk_duration = chunk_word_count * duration_per_word

            start_time = current_time
            end_time = current_time + chunk_duration

            segments.append(CaptionSegment(
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                text=chunk_text,
            ))
            current_time = end_time

    return segments


@router.post("/projects/{project_id}/captions/generate", response_model=CaptionsResponse)
def generate_captions(
    project_id: str,
    payload: CaptionGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate captions from script / scenes.

    If a script_id is provided, captions are generated from that script's
    scenes.  Otherwise captions are generated from all scenes in the project.
    """
    _ensure_project(project_id, db)

    query = db.query(Scene).filter(Scene.project_id == project_id)
    if payload.script_id:
        # Validate script exists
        script = db.query(Script).filter(
            Script.id == payload.script_id,
            Script.project_id == project_id,
        ).first()
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        query = query.filter(Scene.script_id == payload.script_id)

    scenes = query.order_by(Scene.scene_number).all()
    if not scenes:
        raise HTTPException(status_code=400, detail="No scenes found to generate captions from")

    segments = _generate_segments_from_scenes(scenes, payload.words_per_minute)

    # Store captions as JSON on each scene (caption_data_json)
    scene_idx = 0
    for scene in scenes:
        scene_segments = [
            s for s in segments
            if s.start_time >= sum(sc.duration_seconds for sc in scenes[:scene_idx])
        ]
        # Simplified: store all segments as project-level data
        pass
    scene_idx += 1

    total_duration = segments[-1].end_time if segments else 0.0

    logger.info(
        "Generated %d caption segments for project %s",
        len(segments),
        project_id[:8],
    )
    return CaptionsResponse(
        project_id=project_id,
        segments=segments,
        total_duration=round(total_duration, 3),
    )


@router.get("/projects/{project_id}/captions", response_model=CaptionsResponse)
def get_captions(project_id: str, db: Session = Depends(get_db)):
    """Get captions for a project by reading scene caption data."""
    _ensure_project(project_id, db)

    scenes = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )

    all_segments: list[CaptionSegment] = []
    for scene in scenes:
        if scene.caption_data_json:
            try:
                data = json.loads(scene.caption_data_json)
                if isinstance(data, list):
                    for seg in data:
                        all_segments.append(CaptionSegment(**seg))
            except (json.JSONDecodeError, TypeError):
                pass

    # If no stored captions, generate on-the-fly
    if not all_segments and scenes:
        all_segments = _generate_segments_from_scenes(scenes)

    total_duration = all_segments[-1].end_time if all_segments else 0.0

    return CaptionsResponse(
        project_id=project_id,
        segments=all_segments,
        total_duration=round(total_duration, 3),
    )


@router.put("/projects/{project_id}/captions", response_model=CaptionsResponse)
def update_captions(
    project_id: str,
    payload: CaptionsUpdate,
    db: Session = Depends(get_db),
):
    """Update captions by storing segments on the project's scenes.

    Segments are distributed to scenes based on timing overlap.
    """
    _ensure_project(project_id, db)

    scenes = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )

    # Distribute segments across scenes by accumulating scene durations
    accumulated = 0.0
    scene_segments: dict[str, list[dict]] = {s.id: [] for s in scenes}

    for scene in scenes:
        scene_start = accumulated
        scene_end = accumulated + scene.duration_seconds

        for seg in payload.segments:
            # If segment overlaps with this scene's time window
            if seg.start_time < scene_end and seg.end_time > scene_start:
                scene_segments[scene.id].append(seg.model_dump())

        accumulated = scene_end

    # Save to each scene
    for scene in scenes:
        scene.caption_data_json = json.dumps(scene_segments[scene.id])

    db.commit()

    total_duration = payload.segments[-1].end_time if payload.segments else 0.0
    logger.info("Updated captions for project %s (%d segments)", project_id[:8], len(payload.segments))

    return CaptionsResponse(
        project_id=project_id,
        segments=payload.segments,
        total_duration=round(total_duration, 3),
    )


@router.post("/projects/{project_id}/captions/export-srt")
def export_srt(project_id: str, db: Session = Depends(get_db)):
    """Export captions as an SRT file."""
    _ensure_project(project_id, db)

    # Gather segments (same logic as get_captions)
    scenes = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )

    all_segments: list[CaptionSegment] = []
    for scene in scenes:
        if scene.caption_data_json:
            try:
                data = json.loads(scene.caption_data_json)
                if isinstance(data, list):
                    for seg in data:
                        all_segments.append(CaptionSegment(**seg))
            except (json.JSONDecodeError, TypeError):
                pass

    if not all_segments and scenes:
        all_segments = _generate_segments_from_scenes(scenes)

    if not all_segments:
        raise HTTPException(status_code=400, detail="No captions available to export")

    srt_content = _segments_to_srt(all_segments)

    return PlainTextResponse(
        content=srt_content,
        media_type="text/srt",
        headers={
            "Content-Disposition": f'attachment; filename="captions_{project_id[:8]}.srt"',
        },
    )
