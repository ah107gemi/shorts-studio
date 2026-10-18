"""
SQLAlchemy ORM models for Shorts Studio.

Every model uses a UUID hex string as its primary key and records
creation / update timestamps automatically.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Helper ───────────────────────────────────────────────────────────────────

def _new_id() -> str:
    """Generate a 32-char hex UUID for use as a default primary key."""
    return uuid4().hex


# ── Project ──────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    niche: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    target_duration_seconds: Mapped[int] = mapped_column(Integer, default=60)
    tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(32), default="youtube_shorts")
    visual_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voice_preference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_w: Mapped[int] = mapped_column(Integer, default=1080)
    resolution_h: Mapped[int] = mapped_column(Integer, default=1920)
    fps: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", index=True,
    )  # draft | planning | production | rendering | completed | archived
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    scripts: Mapped[list["Script"]] = relationship(
        "Script", back_populates="project", cascade="all, delete-orphan",
    )
    scenes: Mapped[list["Scene"]] = relationship(
        "Scene", back_populates="project", cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="project", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_projects_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Project {self.id[:8]} name={self.name!r}>"


# ── Script ───────────────────────────────────────────────────────────────────

class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="draft",
    )  # draft | approved | archived
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="scripts")
    scenes: Mapped[list["Scene"]] = relationship(
        "Scene", back_populates="script", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_scripts_project_version", "project_id", "version"),
    )

    def __repr__(self) -> str:
        return f"<Script {self.id[:8]} v{self.version}>"


# ── Scene ────────────────────────────────────────────────────────────────────

class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    script_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    on_screen_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    transition: Mapped[str] = mapped_column(String(32), default="crossfade")
    music_cue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sound_effect_cue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True,
    )
    voiceover_asset_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True,
    )
    caption_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    script: Mapped["Script"] = relationship("Script", back_populates="scenes")
    asset: Mapped["Asset | None"] = relationship(
        "Asset", foreign_keys=[asset_id], backref="scenes_as_visual",
    )
    voiceover_asset: Mapped["Asset | None"] = relationship(
        "Asset", foreign_keys=[voiceover_asset_id], backref="scenes_as_voiceover",
    )

    __table_args__ = (
        Index("ix_scenes_project_number", "project_id", "scene_number"),
    )

    def __repr__(self) -> str:
        return f"<Scene {self.id[:8]} #{self.scene_number}>"


# ── Asset ────────────────────────────────────────────────────────────────────

class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
    )  # image | video | audio | music | sound_effect | voiceover | graphic | subtitle
    source: Mapped[str] = mapped_column(
        String(32), default="imported",
    )  # imported | generated | stock | procedural
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    license_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generation_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="assets")

    __table_args__ = (
        Index("ix_assets_project_type", "project_id", "asset_type"),
    )

    def __repr__(self) -> str:
        return f"<Asset {self.id[:8]} type={self.asset_type}>"


# ── Job ──────────────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )  # script_generation | voiceover | render | …
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True,
    )  # pending | queued | running | completed | failed | cancelled | waiting_approval
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_stage: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependencies_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")

    __table_args__ = (
        Index("ix_jobs_project_status", "project_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Job {self.id[:8]} type={self.job_type} status={self.status}>"


# ── ProjectPreset ────────────────────────────────────────────────────────────

class ProjectPreset(Base):
    __tablename__ = "project_presets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProjectPreset {self.id[:8]} name={self.name!r}>"


# ── ProviderConfig ───────────────────────────────────────────────────────────

class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )  # llm | tts | image | video | …
    api_key_set: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    test_result: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<ProviderConfig {self.provider_name!r}>"
