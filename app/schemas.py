"""
Pydantic schemas for Shorts Studio API request/response validation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
#  Project
# ─────────────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    topic: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    language: str = "en"
    target_duration_seconds: int = 60
    tone: Optional[str] = None
    style: Optional[str] = None
    platform: str = "youtube_shorts"
    visual_style: Optional[str] = None
    voice_preference: Optional[str] = None
    resolution_w: int = 1080
    resolution_h: int = 1920
    fps: int = 30
    settings_json: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    topic: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    language: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    platform: Optional[str] = None
    visual_style: Optional[str] = None
    voice_preference: Optional[str] = None
    resolution_w: Optional[int] = None
    resolution_h: Optional[int] = None
    fps: Optional[int] = None
    status: Optional[str] = None
    settings_json: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    topic: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    language: str
    target_duration_seconds: int
    tone: Optional[str] = None
    style: Optional[str] = None
    platform: str
    visual_style: Optional[str] = None
    voice_preference: Optional[str] = None
    resolution_w: int
    resolution_h: int
    fps: int
    status: str
    created_at: datetime
    updated_at: datetime
    settings_json: Optional[str] = None


class ProjectDetailResponse(ProjectResponse):
    """Project response enriched with counts and nested data."""
    script_count: int = 0
    scene_count: int = 0
    asset_count: int = 0


class ProjectStatsResponse(BaseModel):
    project_id: str
    script_count: int = 0
    scene_count: int = 0
    asset_count: int = 0
    job_count: int = 0
    total_scene_duration: float = 0.0
    completed_jobs: int = 0
    failed_jobs: int = 0


# ─────────────────────────────────────────────────────────────────────────────
#  Script
# ─────────────────────────────────────────────────────────────────────────────

class ScriptCreate(BaseModel):
    content: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    conclusion: Optional[str] = None
    cta: Optional[str] = None
    notes: Optional[str] = None


class ScriptUpdate(BaseModel):
    content: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    conclusion: Optional[str] = None
    cta: Optional[str] = None
    notes: Optional[str] = None


class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version: int
    content: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    conclusion: Optional[str] = None
    cta: Optional[str] = None
    word_count: Optional[int] = None
    estimated_duration_seconds: Optional[float] = None
    status: str
    is_approved: bool
    created_at: datetime
    notes: Optional[str] = None


class ScriptGenerateRequest(BaseModel):
    topic: Optional[str] = None
    tone: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    additional_instructions: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Scene
# ─────────────────────────────────────────────────────────────────────────────

class SceneCreate(BaseModel):
    script_id: str
    scene_number: int = 1
    narration_text: Optional[str] = None
    visual_description: Optional[str] = None
    on_screen_text: Optional[str] = None
    duration_seconds: float = 5.0
    transition: str = "crossfade"
    music_cue: Optional[str] = None
    sound_effect_cue: Optional[str] = None
    caption_data_json: Optional[str] = None


class SceneUpdate(BaseModel):
    narration_text: Optional[str] = None
    visual_description: Optional[str] = None
    on_screen_text: Optional[str] = None
    duration_seconds: Optional[float] = None
    transition: Optional[str] = None
    music_cue: Optional[str] = None
    sound_effect_cue: Optional[str] = None
    asset_id: Optional[str] = None
    voiceover_asset_id: Optional[str] = None
    caption_data_json: Optional[str] = None


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    script_id: str
    scene_number: int
    narration_text: Optional[str] = None
    visual_description: Optional[str] = None
    on_screen_text: Optional[str] = None
    duration_seconds: float
    transition: str
    music_cue: Optional[str] = None
    sound_effect_cue: Optional[str] = None
    asset_id: Optional[str] = None
    voiceover_asset_id: Optional[str] = None
    caption_data_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    asset_url: Optional[str] = None
    asset_filename: Optional[str] = None


class SceneReorderRequest(BaseModel):
    scene_ids: list[str] = Field(..., min_length=1)


# ─────────────────────────────────────────────────────────────────────────────
#  Asset
# ─────────────────────────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    original_filename: Optional[str] = None
    file_path: str
    asset_type: str
    source: str
    source_url: Optional[str] = None
    license_info: Optional[str] = None
    generation_settings_json: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    tags: Optional[str] = None
    url: Optional[str] = None


class AssetAssignRequest(BaseModel):
    role: str = Field("visual", pattern="^(visual|voiceover)$")


# ─────────────────────────────────────────────────────────────────────────────
#  Job
# ─────────────────────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    job_type: str
    status: str
    progress: float
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    result_json: Optional[str] = None
    dependencies_json: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
#  Provider / Settings
# ─────────────────────────────────────────────────────────────────────────────

class ProviderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_name: str
    provider_type: str
    api_key_set: bool
    is_enabled: bool
    config_json: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    test_result: Optional[str] = None


class ProviderConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    is_enabled: Optional[bool] = None
    config_json: Optional[str] = None


class ProviderTestResponse(BaseModel):
    provider_name: str
    success: bool
    message: str
    tested_at: datetime


class SystemInfoResponse(BaseModel):
    ffmpeg_available: bool
    ffmpeg_path: Optional[str] = None
    disk_free_bytes: Optional[int] = None
    disk_total_bytes: Optional[int] = None
    python_version: str
    app_version: str
    database_url: str


class AppSettingsResponse(BaseModel):
    tts_provider: str
    llm_provider: str
    image_provider: str
    default_resolution_w: int
    default_resolution_h: int
    default_fps: int
    max_concurrent_renders: int
    log_level: str


class AppSettingsUpdate(BaseModel):
    tts_provider: Optional[str] = None
    llm_provider: Optional[str] = None
    image_provider: Optional[str] = None
    default_resolution_w: Optional[int] = None
    default_resolution_h: Optional[int] = None
    default_fps: Optional[int] = None
    max_concurrent_renders: Optional[int] = None
    log_level: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Render
# ─────────────────────────────────────────────────────────────────────────────

class RenderStartRequest(BaseModel):
    resolution_w: Optional[int] = None
    resolution_h: Optional[int] = None
    fps: Optional[int] = None
    quality: str = Field("high", pattern="^(low|medium|high)$")
    output_format: str = Field("mp4", pattern="^(mp4|webm|mov)$")


class RenderStatusResponse(BaseModel):
    project_id: str
    job_id: Optional[str] = None
    status: str
    progress: float = 0.0
    current_stage: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class RenderQueueItem(BaseModel):
    job_id: str
    project_id: str
    project_name: str
    status: str
    progress: float
    created_at: datetime


class RenderQueueResponse(BaseModel):
    queue: list[RenderQueueItem] = []
    active_count: int = 0
    pending_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
#  Quality
# ─────────────────────────────────────────────────────────────────────────────

class QualityCheckItem(BaseModel):
    check_name: str
    status: str  # pass | warning | fail
    message: str
    details: Optional[dict[str, Any]] = None


class QualityReportResponse(BaseModel):
    project_id: str
    overall_status: str  # pass | warning | fail
    checks: list[QualityCheckItem] = []
    checked_at: datetime
    score: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  Captions
# ─────────────────────────────────────────────────────────────────────────────

class CaptionSegment(BaseModel):
    start_time: float
    end_time: float
    text: str
    style: Optional[str] = None


class CaptionsResponse(BaseModel):
    project_id: str
    segments: list[CaptionSegment] = []
    total_duration: float = 0.0


class CaptionsUpdate(BaseModel):
    segments: list[CaptionSegment]


class CaptionGenerateRequest(BaseModel):
    script_id: Optional[str] = None
    words_per_minute: float = 150.0
    style: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Generic helpers
# ─────────────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Generic message envelope for simple confirmations."""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the global exception handler."""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    uptime_seconds: Optional[float] = None
    ffmpeg_available: bool = False
    ffmpeg: bool = False
    providers: Optional[dict[str, Any]] = None
