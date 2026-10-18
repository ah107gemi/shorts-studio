"""
Asset management routes for Shorts Studio.
Supports both project-scoped and global asset operations.
"""

import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Asset, Project, Scene
from app.schemas import AssetResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Maps MIME type prefixes to asset types
_MIME_TYPE_MAP: dict[str, str] = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
}


def _guess_asset_type(mime_type: str | None, filename: str) -> str:
    """Infer the asset_type from MIME type or file extension."""
    if mime_type:
        for prefix, atype in _MIME_TYPE_MAP.items():
            if mime_type.startswith(prefix):
                return atype
    ext = Path(filename).suffix.lower()
    ext_map: dict[str, str] = {
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
        ".webp": "image", ".svg": "graphic",
        ".mp4": "video", ".mov": "video", ".webm": "video", ".avi": "video",
        ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".aac": "audio",
        ".flac": "audio", ".m4a": "audio",
        ".srt": "subtitle", ".vtt": "subtitle",
    }
    return ext_map.get(ext, "image")


def _ensure_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_or_create_default_project(db: Session) -> Project:
    """Get the most recently updated project, or create a default one if none exist."""
    project = db.query(Project).order_by(Project.updated_at.desc()).first()
    if not project:
        project = Project(
            name="Default Project",
            topic="General Video",
            niche="general",
            language="en",
            target_duration_seconds=60,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info("Created default project %s for asset storage", project.id[:8])
    return project


def _to_asset_response(asset: Asset) -> AssetResponse:
    """Convert ORM asset to schema and include playable/viewable url."""
    res = AssetResponse.model_validate(asset)
    res.url = f"/api/v1/assets/{asset.id}/file"
    return res


async def _save_uploaded_file(file: UploadFile, project_id: str, db: Session) -> Asset:
    """Core logic to save uploaded file and record asset in database."""
    project_assets_dir = Path(settings.PROJECTS_DIR) / project_id / "assets"
    project_assets_dir.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "untitled"
    ext = Path(original_filename).suffix
    safe_filename = f"{uuid4().hex[:12]}{ext}"
    dest_path = project_assets_dir / safe_filename

    content = await file.read()
    dest_path.write_bytes(content)

    mime_type = file.content_type or mimetypes.guess_type(original_filename)[0]
    asset_type = _guess_asset_type(mime_type, original_filename)

    asset = Asset(
        project_id=project_id,
        filename=safe_filename,
        original_filename=original_filename,
        file_path=str(dest_path),
        asset_type=asset_type,
        source="imported",
        mime_type=mime_type,
        file_size_bytes=len(content),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info("Uploaded asset %s (%s) for project %s", asset.id[:8], original_filename, project_id[:8])
    return asset


# ── Upload Routes ────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/assets/upload", response_model=AssetResponse, status_code=201)
@router.post("/projects/{project_id}/assets", response_model=AssetResponse, status_code=201)
async def upload_project_asset(
    project_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """Upload a file associated with a specific project."""
    _ensure_project(project_id, db)
    asset = await _save_uploaded_file(file, project_id, db)
    return _to_asset_response(asset)


@router.post("/assets/upload", response_model=AssetResponse, status_code=201)
@router.post("/assets", response_model=AssetResponse, status_code=201)
async def upload_asset_generic(
    file: UploadFile,
    project_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a file to /assets (accepts optional project_id form field, falls back to active project)."""
    if project_id:
        target_project = db.query(Project).filter(Project.id == project_id).first()
        if not target_project:
            target_project = _get_or_create_default_project(db)
    else:
        target_project = _get_or_create_default_project(db)

    asset = await _save_uploaded_file(file, target_project.id, db)
    return _to_asset_response(asset)


# ── Listing Routes ───────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/assets", response_model=list[AssetResponse])
def list_project_assets(
    project_id: str,
    asset_type: str | None = Query(None, description="Filter by asset type"),
    db: Session = Depends(get_db),
):
    """List project assets with optional type filter."""
    _ensure_project(project_id, db)
    query = db.query(Asset).filter(Asset.project_id == project_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    assets = query.order_by(Asset.created_at.desc()).all()
    return [_to_asset_response(a) for a in assets]


@router.get("/assets", response_model=list[AssetResponse])
def list_all_assets(
    project_id: str | None = Query(None, description="Optional project filter"),
    asset_type: str | None = Query(None, description="Filter by asset type"),
    db: Session = Depends(get_db),
):
    """List all assets across projects or filter by project/type."""
    query = db.query(Asset)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    assets = query.order_by(Asset.created_at.desc()).all()
    return [_to_asset_response(a) for a in assets]


# ── Single Asset Details & File Serving ──────────────────────────────────────

@router.get("/projects/{project_id}/assets/{asset_id}", response_model=AssetResponse)
def get_project_asset(project_id: str, asset_id: str, db: Session = Depends(get_db)):
    """Get asset details within project."""
    asset = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.project_id == project_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _to_asset_response(asset)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset_by_id(asset_id: str, db: Session = Depends(get_db)):
    """Get asset details by asset ID."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _to_asset_response(asset)


@router.get("/projects/{project_id}/assets/{asset_id}/file")
@router.get("/assets/{asset_id}/file")
def serve_asset_file(asset_id: str, project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Serve the raw asset file."""
    query = db.query(Asset).filter(Asset.id == asset_id)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    asset = query.first()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    file_path = Path(asset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=asset.mime_type or "application/octet-stream",
        filename=asset.original_filename or asset.filename,
    )


# ── Deletion Routes ──────────────────────────────────────────────────────────

@router.delete("/projects/{project_id}/assets/{asset_id}", response_model=MessageResponse)
@router.delete("/assets/{asset_id}", response_model=MessageResponse)
def delete_asset(asset_id: str, project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Move an asset to trash (rename on disk, remove from DB)."""
    query = db.query(Asset).filter(Asset.id == asset_id)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    asset = query.first()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Move file to a .trash directory instead of hard deleting
    file_path = Path(asset.file_path)
    if file_path.exists():
        trash_dir = file_path.parent / ".trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        trash_dest = trash_dir / file_path.name
        try:
            shutil.move(str(file_path), str(trash_dest))
            logger.info("Moved asset file to trash: %s", trash_dest)
        except Exception as e:
            logger.warning("Could not move asset to trash: %s", e)

    pid = asset.project_id
    db.delete(asset)
    db.commit()
    logger.info("Deleted asset %s from project %s", asset_id[:8], pid[:8])
    return MessageResponse(message="Asset deleted", detail=asset_id)


# ── Scene Assignment Routes ──────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/assets/{asset_id}/assign/{scene_id}",
    response_model=MessageResponse,
)
def assign_asset_to_scene(
    project_id: str,
    asset_id: str,
    scene_id: str,
    role: str = Query("visual", pattern="^(visual|voiceover)$"),
    db: Session = Depends(get_db),
):
    """Assign an asset to a scene as either visual or voiceover."""
    asset = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.project_id == project_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    scene = (
        db.query(Scene)
        .filter(Scene.id == scene_id, Scene.project_id == project_id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    if role == "voiceover":
        scene.voiceover_asset_id = asset_id
    else:
        scene.asset_id = asset_id

    db.commit()
    logger.info("Assigned asset %s as %s to scene %s", asset_id[:8], role, scene_id[:8])
    return MessageResponse(
        message=f"Asset assigned as {role}",
        detail=f"asset={asset_id}, scene={scene_id}",
    )


class SceneAssetAssignPayload(BaseModel):
    asset_id: str
    role: Optional[str] = "visual"


@router.put(
    "/projects/{project_id}/scenes/{scene_id}/asset",
    response_model=MessageResponse,
)
def assign_scene_asset_alt(
    project_id: str,
    scene_id: str,
    payload: SceneAssetAssignPayload,
    db: Session = Depends(get_db),
):
    """Alternative assignment endpoint matching frontend PUT /scenes/{scene_id}/asset."""
    return assign_asset_to_scene(
        project_id=project_id,
        asset_id=payload.asset_id,
        scene_id=scene_id,
        role=payload.role or "visual",
        db=db,
    )
