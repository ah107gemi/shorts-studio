"""
End-to-End Test Suite for Shorts Studio.
Tests Project management, Scripts, Scenes, Voiceover, Captions, Quality Control, and FFmpeg Video Assembly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models import Asset, Job, Project, Scene, Script
from app.services.video_engine import VideoEngine
from app.services.voice_engine import VoiceEngine


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database and data directories are initialized."""
    settings.ensure_directories()
    init_db()
    yield


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint and verify FFmpeg detection."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["ffmpeg_available"] is True
    assert data["ffmpeg"] is True


def test_project_crud(client):
    """Test creating, reading, updating, and listing projects."""
    payload = {
        "name": "Test Space Facts",
        "topic": "The Deep Space Mysteries",
        "niche": "educational",
        "target_audience": "Curious viewers",
        "language": "en",
        "target_duration_seconds": 30,
        "tone": "mysterious",
        "style": "cinematic",
        "platform": "youtube_shorts",
        "resolution_w": 1080,
        "resolution_h": 1920,
        "fps": 30,
    }
    # 1. Create
    res = client.post("/api/v1/projects", json=payload)
    assert res.status_code == 201
    proj = res.json()
    assert proj["name"] == "Test Space Facts"
    proj_id = proj["id"]

    # 2. Get by ID
    res_get = client.get(f"/api/v1/projects/{proj_id}")
    assert res_get.status_code == 200
    assert res_get.json()["topic"] == "The Deep Space Mysteries"

    # 3. Update
    res_up = client.put(f"/api/v1/projects/{proj_id}", json={"tone": "dramatic"})
    assert res_up.status_code == 200
    assert res_up.json()["tone"] == "dramatic"

    # 4. List
    res_list = client.get("/api/v1/projects")
    assert res_list.status_code == 200
    assert any(p["id"] == proj_id for p in res_list.json())


def test_script_and_scenes_flow(client):
    """Test creating script, approving, and auto-splitting into scenes."""
    # Create project
    res_p = client.post("/api/v1/projects", json={"name": "Script Test Short"})
    proj_id = res_p.json()["id"]

    # Create script
    script_payload = {
        "hook": "Did you know that neutron stars spin 600 times a second?",
        "body": "When a massive star collapses, its core compresses down into a sphere just 20 kilometers across with unfathomable gravity.",
        "conclusion": "A single teaspoon of its material would weigh billions of tons.",
        "cta": "Subscribe for more incredible cosmic discoveries!",
        "content": "Full combined script text",
    }
    res_s = client.post(f"/api/v1/projects/{proj_id}/scripts", json=script_payload)
    assert res_s.status_code == 201
    script = res_s.json()
    script_id = script["id"]
    assert script["word_count"] > 20
    assert script["estimated_duration_seconds"] > 5.0
    assert script["is_approved"] is False

    # Approve script
    res_app = client.post(f"/api/v1/projects/{proj_id}/scripts/{script_id}/approve")
    assert res_app.status_code == 200
    assert res_app.json()["is_approved"] is True

    # Auto-split into scenes from script
    res_split = client.post(f"/api/v1/projects/{proj_id}/scenes/from-script/{script_id}")
    assert res_split.status_code == 201
    scenes = res_split.json()
    assert len(scenes) == 4  # Hook, Body, Conclusion, CTA
    assert scenes[0]["narration_text"] == script_payload["hook"]
    assert scenes[1]["narration_text"] == script_payload["body"]


def test_captions_generation_and_export(client):
    """Test generating captions and exporting SRT file."""
    # Create project with scenes
    res_p = client.post("/api/v1/projects", json={"name": "Captions Test Short"})
    proj_id = res_p.json()["id"]

    res_s = client.post(
        f"/api/v1/projects/{proj_id}/scripts",
        json={"hook": "Scientists just found water on Mars.", "content": "Scientists just found water on Mars."},
    )
    script_id = res_s.json()["id"]
    client.post(f"/api/v1/projects/{proj_id}/scenes/from-script/{script_id}")

    # Generate captions
    res_cap = client.post(f"/api/v1/projects/{proj_id}/captions/generate", json={})
    assert res_cap.status_code == 200
    captions = res_cap.json()
    assert len(captions["segments"]) > 0

    # Export SRT
    res_srt = client.post(f"/api/v1/projects/{proj_id}/captions/export-srt")
    assert res_srt.status_code == 200
    assert "-->" in res_srt.text
    assert "Scientists" in res_srt.text


def test_quality_checks(client):
    """Test automated quality checks for a project."""
    res_p = client.post("/api/v1/projects", json={"name": "QC Test Short", "target_duration_seconds": 15})
    proj_id = res_p.json()["id"]

    res_qc = client.post(f"/api/v1/projects/{proj_id}/quality-check")
    assert res_qc.status_code == 200
    report = res_qc.json()
    assert "checks" in report
    assert "overall_status" in report
    assert report["score"] is not None


def test_voiceover_synthesis():
    """Test local speech synthesizer creating a real audio file."""
    test_audio = Path(settings.CACHE_DIR) / "test_synth.wav"
    ok = VoiceEngine.generate_voiceover(
        text="This is a test narration for Shorts Studio video generation.",
        output_path=test_audio,
    )
    assert ok is True
    assert test_audio.exists()
    assert test_audio.stat().st_size > 500


def test_ffmpeg_video_assembly_real():
    """Test end-to-end FFmpeg assembly producing a playable vertical 9:16 MP4 video."""
    output_mp4 = Path(settings.CACHE_DIR) / "test_render_short.mp4"
    if output_mp4.exists():
        output_mp4.unlink()

    scenes = [
        {
            "scene_number": 1,
            "duration_seconds": 2.0,
            "narration_text": "Did you know that honey never spoils?",
            "visual_description": "Ancient Golden Honey Jar",
        },
        {
            "scene_number": 2,
            "duration_seconds": 2.5,
            "narration_text": "Archaeologists found 3000-year-old honey that was still edible.",
            "visual_description": "Egyptian Tomb Discovery",
        },
    ]

    success = VideoEngine.render_project_video(
        project_id="test_proj_render",
        scenes=scenes,
        output_file=output_mp4,
        resolution_w=540,
        resolution_h=960,  # Fast 9:16 preview scale
        fps=24,
        is_preview=True,
    )
    assert success is True
    assert output_mp4.exists()

    # Validate output media streams using ffprobe
    validation = VideoEngine.validate_output_video(output_mp4, expected_w=540, expected_h=960)
    assert validation["valid"] is True
    assert validation["has_video"] is True
    assert validation["has_audio"] is True
    assert validation["duration"] >= 3.5
    assert validation["size_bytes"] > 20000
