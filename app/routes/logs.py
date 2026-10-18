"""
Logs and diagnostic inspection routes for Shorts Studio.
"""

import logging
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class LogsResponse(BaseModel):
    lines: list[str] = []
    total_lines: int = 0


@router.get("/logs", response_model=LogsResponse)
def get_logs(limit: int = 200):
    """Retrieve recent application logs."""
    log_file = Path(settings.LOGS_DIR) / "shorts_studio.log"
    if not log_file.exists():
        return LogsResponse(lines=["[INFO] Log file not yet created"], total_lines=1)

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent = [line.strip() for line in all_lines[-limit:] if line.strip()]
            return LogsResponse(lines=recent, total_lines=len(all_lines))
    except Exception as e:
        logger.error("Error reading log file: %s", e)
        return LogsResponse(lines=[f"[ERROR] Could not read log file: {e}"], total_lines=1)
