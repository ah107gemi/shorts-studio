"""
Scene management routes for Shorts Studio.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Project, Scene, Script
from app.schemas import (
    MessageResponse,
    SceneCreate,
    SceneReorderRequest,
    SceneResponse,
    SceneUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _enrich_scene_response(scene: Scene, db: Session) -> SceneResponse:
    """Populate asset_url and asset_filename from Asset table if asset_id is set."""
    res = SceneResponse.model_validate(scene)
    if scene.asset_id:
        asset = db.query(Asset).filter(Asset.id == scene.asset_id).first()
        if asset:
            res.asset_url = f"/api/v1/assets/{asset.id}/file"
            res.asset_filename = asset.original_filename or asset.filename
    return res


def _renumber_scenes(project_id: str, db: Session) -> None:
    """Re-assign consecutive scene_number values starting from 1."""
    scenes = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )
    for idx, scene in enumerate(scenes, start=1):
        scene.scene_number = idx


@router.post("/projects/{project_id}/scenes", response_model=SceneResponse, status_code=201)
def create_scene(project_id: str, payload: SceneCreate, db: Session = Depends(get_db)):
    """Create a new scene."""
    _ensure_project(project_id, db)

    # Verify script exists
    script = db.query(Script).filter(
        Script.id == payload.script_id,
        Script.project_id == project_id,
    ).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found in this project")

    scene = Scene(project_id=project_id, **payload.model_dump())
    db.add(scene)
    db.commit()
    db.refresh(scene)
    logger.info("Created scene #%d for project %s", scene.scene_number, project_id[:8])
    return _enrich_scene_response(scene, db)


@router.get("/projects/{project_id}/scenes", response_model=list[SceneResponse])
def list_scenes(project_id: str, db: Session = Depends(get_db)):
    """List scenes ordered by scene_number."""
    _ensure_project(project_id, db)
    scenes = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )
    return [_enrich_scene_response(s, db) for s in scenes]


@router.put("/projects/{project_id}/scenes/{scene_id}", response_model=SceneResponse)
def update_scene(
    project_id: str,
    scene_id: str,
    payload: SceneUpdate,
    db: Session = Depends(get_db),
):
    """Update a scene."""
    scene = (
        db.query(Scene)
        .filter(Scene.id == scene_id, Scene.project_id == project_id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scene, field, value)

    db.commit()
    db.refresh(scene)
    logger.info("Updated scene %s", scene_id[:8])
    return _enrich_scene_response(scene, db)


@router.delete("/projects/{project_id}/scenes/{scene_id}", response_model=MessageResponse)
def delete_scene(project_id: str, scene_id: str, db: Session = Depends(get_db)):
    """Delete a scene and renumber remaining scenes."""
    scene = (
        db.query(Scene)
        .filter(Scene.id == scene_id, Scene.project_id == project_id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    db.delete(scene)
    db.flush()
    _renumber_scenes(project_id, db)
    db.commit()
    logger.info("Deleted scene %s and renumbered", scene_id[:8])
    return MessageResponse(message="Scene deleted", detail=scene_id)


@router.post("/projects/{project_id}/scenes/reorder", response_model=list[SceneResponse])
def reorder_scenes(
    project_id: str,
    payload: SceneReorderRequest,
    db: Session = Depends(get_db),
):
    """Reorder scenes by providing the full list of scene IDs in desired order."""
    _ensure_project(project_id, db)

    scenes_by_id: dict[str, Scene] = {}
    for sid in payload.scene_ids:
        scene = db.query(Scene).filter(
            Scene.id == sid,
            Scene.project_id == project_id,
        ).first()
        if not scene:
            raise HTTPException(status_code=404, detail=f"Scene {sid} not found")
        scenes_by_id[sid] = scene

    # Assign new order
    for idx, sid in enumerate(payload.scene_ids, start=1):
        scenes_by_id[sid].scene_number = idx

    db.commit()

    ordered = (
        db.query(Scene)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number)
        .all()
    )
    logger.info("Reordered %d scenes for project %s", len(ordered), project_id[:8])
    return ordered


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/duplicate",
    response_model=SceneResponse,
    status_code=201,
)
def duplicate_scene(project_id: str, scene_id: str, db: Session = Depends(get_db)):
    """Duplicate a scene, placing the copy immediately after the original."""
    original = (
        db.query(Scene)
        .filter(Scene.id == scene_id, Scene.project_id == project_id)
        .first()
    )
    if not original:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Shift scenes after the original
    subsequent = (
        db.query(Scene)
        .filter(Scene.project_id == project_id, Scene.scene_number > original.scene_number)
        .order_by(Scene.scene_number.desc())
        .all()
    )
    for s in subsequent:
        s.scene_number += 1

    new_scene = Scene(
        project_id=project_id,
        script_id=original.script_id,
        scene_number=original.scene_number + 1,
        narration_text=original.narration_text,
        visual_description=original.visual_description,
        on_screen_text=original.on_screen_text,
        duration_seconds=original.duration_seconds,
        transition=original.transition,
        music_cue=original.music_cue,
        sound_effect_cue=original.sound_effect_cue,
        caption_data_json=original.caption_data_json,
    )
    db.add(new_scene)
    db.commit()
    db.refresh(new_scene)
    logger.info("Duplicated scene %s → %s", scene_id[:8], new_scene.id[:8])
    return new_scene


@router.post(
    "/projects/{project_id}/scenes/from-script/{script_id}",
    response_model=list[SceneResponse],
    status_code=201,
)
def scenes_from_script(project_id: str, script_id: str, db: Session = Depends(get_db)):
    """Auto-split a script into scenes.

    Splitting strategy:
    1. If the script has structured parts (hook, body, conclusion, cta), create
       one scene per non-empty part.
    2. Otherwise, split the content on double-newlines / sentence boundaries
       aiming for roughly 15-second segments (~37 words each at 150 wpm).
    """
    _ensure_project(project_id, db)

    script = db.query(Script).filter(
        Script.id == script_id,
        Script.project_id == project_id,
    ).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Delete existing scenes for this script so we can regenerate
    db.query(Scene).filter(
        Scene.project_id == project_id,
        Scene.script_id == script_id,
    ).delete()
    db.flush()

    segments: list[tuple[str, str]] = []  # (label, text)

    # Strategy 1: structured parts
    structured_parts = [
        ("Hook", script.hook),
        ("Body", script.body),
        ("Conclusion", script.conclusion),
        ("Call to Action", script.cta),
    ]
    has_structured = any(text for _, text in structured_parts)

    if has_structured:
        for label, text in structured_parts:
            if text and text.strip():
                segments.append((label, text.strip()))
    elif script.content:
        # Strategy 2: split on double-newlines, then on sentence boundaries
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", script.content) if p.strip()]
        if not paragraphs:
            paragraphs = [script.content.strip()]
        for i, para in enumerate(paragraphs, 1):
            segments.append((f"Scene {i}", para))

    if not segments:
        raise HTTPException(
            status_code=400,
            detail="Script has no content to split into scenes",
        )

    # Determine the starting scene_number (after any existing scenes)
    max_scene_num = (
        db.query(Scene.scene_number)
        .filter(Scene.project_id == project_id)
        .order_by(Scene.scene_number.desc())
        .limit(1)
        .scalar() or 0
    )

    created_scenes: list[Scene] = []
    for idx, (label, text) in enumerate(segments, start=1):
        word_count = len(text.split())
        duration = round((word_count / 150.0) * 60, 2)
        duration = max(duration, 2.0)  # Minimum 2 seconds

        scene = Scene(
            project_id=project_id,
            script_id=script_id,
            scene_number=max_scene_num + idx,
            narration_text=text,
            visual_description=f"[{label}] Visual for: {text[:80]}…" if len(text) > 80 else f"[{label}] Visual for: {text}",
            duration_seconds=duration,
        )
        db.add(scene)
        created_scenes.append(scene)

    db.commit()
    for s in created_scenes:
        db.refresh(s)

    logger.info("Created %d scenes from script %s", len(created_scenes), script_id[:8])
    return created_scenes
