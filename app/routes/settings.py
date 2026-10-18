"""
Settings and provider configuration routes for Shorts Studio.
"""

import logging
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ProviderConfig
from app.schemas import (
    AppSettingsResponse,
    AppSettingsUpdate,
    MessageResponse,
    ProviderConfigResponse,
    ProviderConfigUpdate,
    ProviderTestResponse,
    SystemInfoResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Maps provider names to environment variable names for API keys
_API_KEY_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "pexels": "PEXELS_API_KEY",
    "pixabay": "PIXABAY_API_KEY",
}


@router.get("/settings/providers", response_model=list[ProviderConfigResponse])
def list_providers(db: Session = Depends(get_db)):
    """List all provider configurations."""
    providers = db.query(ProviderConfig).order_by(ProviderConfig.provider_name).all()
    return providers


@router.put("/settings/providers/{provider_name}", response_model=ProviderConfigResponse)
def update_provider(
    provider_name: str,
    payload: ProviderConfigUpdate,
    db: Session = Depends(get_db),
):
    """Update a provider configuration.

    If an api_key is supplied it is stored in the process environment (NOT in
    the database) and the ``api_key_set`` flag is set to True.
    """
    provider = (
        db.query(ProviderConfig)
        .filter(ProviderConfig.provider_name == provider_name)
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    # Handle API key – store in env, set flag in DB
    if payload.api_key is not None:
        env_var = _API_KEY_ENV_MAP.get(provider_name)
        if env_var:
            os.environ[env_var] = payload.api_key
            logger.info("Set environment variable %s", env_var)
        provider.api_key_set = bool(payload.api_key)

    if payload.is_enabled is not None:
        provider.is_enabled = payload.is_enabled

    if payload.config_json is not None:
        provider.config_json = payload.config_json

    db.commit()
    db.refresh(provider)
    logger.info("Updated provider %s", provider_name)
    return provider


@router.post("/settings/providers/{provider_name}/test", response_model=ProviderTestResponse)
def test_provider(provider_name: str, db: Session = Depends(get_db)):
    """Test a provider connection.

    For now this performs a lightweight check: verifies that the API key
    environment variable is set and non-empty.  Future versions will make
    a real API call.
    """
    provider = (
        db.query(ProviderConfig)
        .filter(ProviderConfig.provider_name == provider_name)
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    env_var = _API_KEY_ENV_MAP.get(provider_name)
    now = datetime.utcnow()

    if env_var and os.environ.get(env_var):
        provider.last_tested_at = now
        provider.test_result = "ok"
        db.commit()
        return ProviderTestResponse(
            provider_name=provider_name,
            success=True,
            message=f"API key for {provider_name} is configured",
            tested_at=now,
        )
    else:
        provider.last_tested_at = now
        provider.test_result = "no_key"
        db.commit()
        return ProviderTestResponse(
            provider_name=provider_name,
            success=False,
            message=f"No API key configured for {provider_name}",
            tested_at=now,
        )


@router.get("/settings/system", response_model=SystemInfoResponse)
def get_system_info():
    """Get system information."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path and settings.FFMPEG_PATH:
        ffmpeg_path = settings.FFMPEG_PATH if Path(settings.FFMPEG_PATH).exists() else None

    # Disk space for the data directory
    disk_free: int | None = None
    disk_total: int | None = None
    try:
        usage = shutil.disk_usage(str(settings.DATA_DIR))
        disk_free = usage.free
        disk_total = usage.total
    except Exception:
        pass

    return SystemInfoResponse(
        ffmpeg_available=ffmpeg_path is not None,
        ffmpeg_path=ffmpeg_path,
        disk_free_bytes=disk_free,
        disk_total_bytes=disk_total,
        python_version=platform.python_version(),
        app_version=settings.APP_VERSION,
        database_url=settings.DATABASE_URL,
    )


@router.get("/settings/app", response_model=AppSettingsResponse)
def get_app_settings():
    """Get current application settings."""
    return AppSettingsResponse(
        tts_provider=settings.TTS_PROVIDER,
        llm_provider=settings.LLM_PROVIDER,
        image_provider=settings.IMAGE_PROVIDER,
        default_resolution_w=settings.DEFAULT_RESOLUTION_W,
        default_resolution_h=settings.DEFAULT_RESOLUTION_H,
        default_fps=settings.DEFAULT_FPS,
        max_concurrent_renders=settings.MAX_CONCURRENT_RENDERS,
        log_level=settings.LOG_LEVEL,
    )


@router.put("/settings/app", response_model=AppSettingsResponse)
def update_app_settings(payload: AppSettingsUpdate):
    """Update application settings (runtime only – does not persist to .env).

    For persistence the caller should also write to the .env file or use a
    configuration management flow.
    """
    update_data = payload.model_dump(exclude_unset=True)

    field_map = {
        "tts_provider": "TTS_PROVIDER",
        "llm_provider": "LLM_PROVIDER",
        "image_provider": "IMAGE_PROVIDER",
        "default_resolution_w": "DEFAULT_RESOLUTION_W",
        "default_resolution_h": "DEFAULT_RESOLUTION_H",
        "default_fps": "DEFAULT_FPS",
        "max_concurrent_renders": "MAX_CONCURRENT_RENDERS",
        "log_level": "LOG_LEVEL",
    }

    for key, value in update_data.items():
        attr = field_map.get(key)
        if attr and hasattr(settings, attr):
            object.__setattr__(settings, attr, value)

    logger.info("Updated app settings: %s", list(update_data.keys()))
    return get_app_settings()
