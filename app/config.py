"""
Application configuration using pydantic-settings.
Loads settings from environment variables and .env file.
"""

import shutil
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Base directory for the entire project
_BASE_DIR = Path(r"d:\Antigravity.google\ShortsStudio")


class Settings(BaseSettings):
    """Central configuration for Shorts Studio."""

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Shorts Studio"
    APP_VERSION: str = "1.0.0"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{(_BASE_DIR / 'data' / 'shorts_studio.db').as_posix()}"

    # ── Directories ──────────────────────────────────────────────────────
    DATA_DIR: Path = _BASE_DIR / "data"
    PROJECTS_DIR: Path = _BASE_DIR / "data" / "projects"
    ASSETS_DIR: Path = _BASE_DIR / "data" / "assets"
    CACHE_DIR: Path = _BASE_DIR / "data" / "cache"
    RENDERS_DIR: Path = _BASE_DIR / "data" / "renders"
    LOGS_DIR: Path = _BASE_DIR / "data" / "logs"

    # ── FFmpeg ───────────────────────────────────────────────────────────
    FFMPEG_PATH: str = ""

    # ── API Keys (all optional) ──────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None

    # ── Provider Selection ───────────────────────────────────────────────
    TTS_PROVIDER: str = "none"
    LLM_PROVIDER: str = "none"
    IMAGE_PROVIDER: str = "none"

    # ── Video Defaults ───────────────────────────────────────────────────
    DEFAULT_RESOLUTION_W: int = 1080
    DEFAULT_RESOLUTION_H: int = 1920
    DEFAULT_FPS: int = 30
    MAX_CONCURRENT_RENDERS: int = 1

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Helpers ──────────────────────────────────────────────────────────

    def ensure_directories(self) -> None:
        """Create every configured directory if it does not already exist."""
        for directory in (
            self.DATA_DIR,
            self.PROJECTS_DIR,
            self.ASSETS_DIR,
            self.CACHE_DIR,
            self.RENDERS_DIR,
            self.LOGS_DIR,
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)

    def detect_ffmpeg(self) -> str:
        """Return the configured FFmpeg path, or try to auto-detect it."""
        if self.FFMPEG_PATH and Path(self.FFMPEG_PATH).exists():
            return self.FFMPEG_PATH
        local_bin = _BASE_DIR / "bin" / "ffmpeg.exe"
        if local_bin.exists():
            return str(local_bin)
        found = shutil.which("ffmpeg")
        return found if found else str(local_bin)


# Module-level singleton – import this from anywhere.
settings = Settings()
