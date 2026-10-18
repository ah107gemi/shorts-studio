"""
End-to-End Production Script: "3 Forbidden Places on Earth"
Builds and renders the complete vertical video project in Shorts Studio
without requiring manual UI steps.
"""

import json
import logging
import math
import os
import shutil
import subprocess
import uuid
import wave
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, r"d:\Antigravity.google\ShortsStudio")

import httpx

# Shorts Studio imports
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Asset, Job, Project, Scene, Script
from app.services.pipeline_orchestrator import orchestrator
from app.services.voice_engine import VoiceEngine
from app.services.video_engine import VideoEngine
from app.routes.captions import _generate_segments_from_scenes, _segments_to_srt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_project")

PROJECT_TITLE = "3 Forbidden Places on Earth"
PROJECT_TOPIC = "Dark Mysteries / Unexplained Forbidden Locations"
RESOLUTION_W = 1080
RESOLUTION_H = 1920
FPS = 30

SCENE_DEFS = [
    {
        "scene_number": 1,
        "role": "Hook",
        "target_duration": 4.0,
        "narration": "If you ever set foot on this island, you will never make it back alive.",
        "visual_desc": "dark moody stormy island surrounded by crashing ocean waves aerial shot",
        "asset_source": "local_video",
        "local_source_path": r"D:\Antigravity.google\ShortsStudio\VIDEOS\PEXEL READY\14710270_540_960_30fps.mp4",
        "target_filename": "14710270_ocean_waves_island.mp4",
        "asset_type": "video",
        "mime_type": "video/mp4",
    },
    {
        "scene_number": 2,
        "role": "Point 1",
        "target_duration": 6.0,
        "narration": "First is North Sentinel Island, home to an isolated tribe that fiercely attacks anyone who approaches.",
        "visual_desc": "dense tropical jungle shoreline ocean waves misty remote island",
        "asset_source": "url",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/North-Sentinel-Island-Sentinel-2A.png",
        "target_filename": "north_sentinel_island.png",
        "asset_type": "image",
        "mime_type": "image/png",
    },
    {
        "scene_number": 3,
        "role": "Point 2",
        "target_duration": 6.0,
        "narration": "Next is Snake Island in Brazil, home to thousands of golden lancehead vipers whose venom melts human flesh.",
        "visual_desc": "misty dark rainforest jungle trees cinematic moody atmosphere",
        "asset_source": "url",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/4d/Ilha_da_Queimada_Grande_-_Itanha%C3%A9m3.jpg",
        "target_filename": "snake_island_brazil.jpg",
        "asset_type": "image",
        "mime_type": "image/jpeg",
    },
    {
        "scene_number": 4,
        "role": "Point 3",
        "target_duration": 6.0,
        "narration": "And the Svalbard Global Seed Vault, built deep into Arctic permafrost to preserve crops after an apocalypse.",
        "visual_desc": "arctic bunker entrance snow mountains freezing blizzard northern lights",
        "asset_source": "url",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Svalbard_Global_Seed_Vault_February_2025.jpg",
        "target_filename": "svalbard_seed_vault.jpg",
        "asset_type": "image",
        "mime_type": "image/jpeg",
    },
    {
        "scene_number": 5,
        "role": "Outro/CTA",
        "target_duration": 4.0,
        "narration": "Which place would you dare visit? Hit subscribe for more forbidden secrets.",
        "visual_desc": "mysterious fog over dark horizon dramatic cinematic lighting",
        "asset_source": "url",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/51/A_foggy_winter_morning.jpg/1280px-A_foggy_winter_morning.jpg",
        "target_filename": "mysterious_fog_landscape.jpg",
        "asset_type": "image",
        "mime_type": "image/jpeg",
    },
]

def get_audio_duration_seconds(audio_path: Path) -> float:
    """Return exact duration of wav audio file."""
    try:
        with wave.open(str(audio_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        # Fallback to ffprobe
        info = VideoEngine.probe_media(str(audio_path))
        if info and "format" in info and "duration" in info["format"]:
            return float(info["format"]["duration"])
    return 5.0

def main():
    logger.info("==================================================")
    logger.info("🎬 Producing: '%s'", PROJECT_TITLE)
    logger.info("==================================================")

    init_db()
    db = SessionLocal()

    # Step 1: Create or reuse Project record
    existing = db.query(Project).filter(Project.name == PROJECT_TITLE).first()
    if existing:
        logger.info("Found existing project '%s' (%s), reusing...", existing.name, existing.id)
        project = existing
        project.status = "draft"
    else:
        project_id = uuid.uuid4().hex
        project = Project(
            id=project_id,
            name=PROJECT_TITLE,
            topic=PROJECT_TOPIC,
            niche="dark_mysteries",
            target_audience="Shorts viewers, mystery and trivia fans",
            language="en",
            platform="youtube_shorts",
            target_duration_seconds=26,
            style="dark_cinematic",
            visual_style="moody_dark",
            resolution_w=RESOLUTION_W,
            resolution_h=RESOLUTION_H,
            fps=FPS,
            status="draft",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info("Created Project record: %s (ID: %s)", project.name, project.id)

    proj_dir = settings.PROJECTS_DIR / project.id
    assets_dir = proj_dir / "assets"
    vo_dir = proj_dir / "voiceover"
    proj_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    vo_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Create Script record
    script = db.query(Script).filter(Script.project_id == project.id).first()
    full_script_content = "\n\n".join([f"Scene {s['scene_number']} ({s['role']}):\n{s['narration']}" for s in SCENE_DEFS])
    if not script:
        script = Script(
            id=uuid.uuid4().hex,
            project_id=project.id,
            version=1,
            content=full_script_content,
            hook=SCENE_DEFS[0]["narration"],
            body="\n\n".join([s["narration"] for s in SCENE_DEFS[1:-1]]),
            conclusion=SCENE_DEFS[-1]["narration"],
            cta=SCENE_DEFS[-1]["narration"],
            word_count=len(full_script_content.split()),
            estimated_duration_seconds=sum([s["target_duration"] for s in SCENE_DEFS]),
            status="approved",
            is_approved=True,
        )
        db.add(script)
        db.commit()
        db.refresh(script)
        logger.info("Created Script record: %s", script.id)
    else:
        script.content = full_script_content
        script.is_approved = True
        db.commit()

    # Step 3: Fetch & Register Visual Assets
    logger.info("Fetching and preparing visual background assets...")
    asset_records = {}
    client = httpx.Client(headers={"User-Agent": "ShortsStudio/1.0 (contact@shorts.studio)"}, timeout=45.0)

    for sc_def in SCENE_DEFS:
        target_file = assets_dir / sc_def["target_filename"]
        if sc_def["asset_source"] == "local_video":
            src = Path(sc_def["local_source_path"])
            if src.exists():
                shutil.copy2(str(src), str(target_file))
                logger.info("✓ Copied local video for Scene %d -> %s", sc_def["scene_number"], target_file.name)
            else:
                logger.warning("Local source %s not found", src)
        elif sc_def["asset_source"] == "url":
            if not target_file.exists() or target_file.stat().st_size < 1000:
                logger.info("Downloading asset for Scene %d from %s ...", sc_def["scene_number"], sc_def["url"])
                resp = client.get(sc_def["url"])
                if resp.status_code == 200:
                    target_file.write_bytes(resp.content)
                    logger.info("✓ Downloaded %s (%d bytes)", target_file.name, target_file.stat().st_size)
                else:
                    logger.warning("Download failed with HTTP %d for %s", resp.status_code, sc_def["url"])

        # Check file exists and register in DB Asset table
        if target_file.exists():
            asset_rec = db.query(Asset).filter(Asset.project_id == project.id, Asset.filename == target_file.name).first()
            if not asset_rec:
                asset_rec = Asset(
                    id=uuid.uuid4().hex,
                    project_id=project.id,
                    filename=target_file.name,
                    original_filename=target_file.name,
                    file_path=str(target_file),
                    asset_type=sc_def["asset_type"],
                    source="stock" if sc_def["asset_source"] == "url" else "imported",
                    mime_type=sc_def["mime_type"],
                    file_size_bytes=target_file.stat().st_size,
                )
                db.add(asset_rec)
                db.commit()
                db.refresh(asset_rec)
            asset_records[sc_def["scene_number"]] = asset_rec
            logger.info("Registered Asset for Scene %d: ID=%s, File=%s", sc_def["scene_number"], asset_rec.id[:8], target_file.name)

    client.close()

    # Step 4: Synthesize Voiceovers & Register Audio Assets
    logger.info("Generating voiceover narration for all 5 scenes...")
    vo_records = {}
    for sc_def in SCENE_DEFS:
        scene_num = sc_def["scene_number"]
        vo_filename = f"scene_{scene_num:02d}_narration.wav"
        vo_path = vo_dir / vo_filename

        logger.info("Synthesizing Scene %d narration: '%s'", scene_num, sc_def["narration"])
        VoiceEngine.generate_voiceover(
            text=sc_def["narration"],
            output_path=vo_path,
            speed=1.05,
        )

        audio_dur = get_audio_duration_seconds(vo_path)
        logger.info("✓ Scene %d audio synthesized: %s (Duration: %.2fs)", scene_num, vo_filename, audio_dur)

        # Register audio asset in DB
        vo_rec = db.query(Asset).filter(Asset.project_id == project.id, Asset.filename == vo_filename).first()
        if not vo_rec:
            vo_rec = Asset(
                id=uuid.uuid4().hex,
                project_id=project.id,
                filename=vo_filename,
                original_filename=vo_filename,
                file_path=str(vo_path),
                asset_type="audio",
                source="tts",
                mime_type="audio/wav",
                file_size_bytes=vo_path.stat().st_size,
                duration_seconds=audio_dur,
            )
            db.add(vo_rec)
            db.commit()
            db.refresh(vo_rec)
        else:
            vo_rec.duration_seconds = audio_dur
            db.commit()
        vo_records[scene_num] = (vo_rec, audio_dur)

    # Step 5: Create or Update Scene Records
    logger.info("Configuring project scenes with timings and caption cues...")
    # Clean previous scenes if any
    db.query(Scene).filter(Scene.project_id == project.id).delete()
    db.commit()

    created_scenes = []
    for sc_def in SCENE_DEFS:
        scene_num = sc_def["scene_number"]
        vo_rec, audio_dur = vo_records[scene_num]
        asset_rec = asset_records.get(scene_num)

        # Ensure duration comfortably accommodates narration + breathing room
        scene_duration = max(sc_def["target_duration"], math.ceil(audio_dur + 0.5))

        # Generate simple scene caption metadata
        words = sc_def["narration"].split()
        dur_per_word = audio_dur / len(words) if words else 0.5
        caption_cues = []
        cur_t = 0.0
        for i in range(0, len(words), 4):
            chunk = words[i:i+4]
            chunk_text = " ".join(chunk)
            end_t = cur_t + (len(chunk) * dur_per_word)
            caption_cues.append({
                "start": round(cur_t, 2),
                "end": round(end_t, 2),
                "text": chunk_text
            })
            cur_t = end_t

        scene = Scene(
            id=uuid.uuid4().hex,
            project_id=project.id,
            script_id=script.id,
            scene_number=scene_num,
            narration_text=sc_def["narration"],
            visual_description=sc_def["visual_desc"],
            duration_seconds=scene_duration,
            transition="crossfade",
            asset_id=asset_rec.id if asset_rec else None,
            voiceover_asset_id=vo_rec.id if vo_rec else None,
            caption_data_json=json.dumps(caption_cues),
        )
        db.add(scene)
        created_scenes.append(scene)

    db.commit()
    logger.info("✓ Created and saved %d scenes in database", len(created_scenes))

    # Step 6: Export Standalone Project JSON Files
    project_dict = {
        "id": project.id,
        "name": project.name,
        "topic": project.topic,
        "niche": project.niche,
        "aspect_ratio": "9:16",
        "resolution_w": project.resolution_w,
        "resolution_h": project.resolution_h,
        "fps": project.fps,
        "created_at": datetime.utcnow().isoformat(),
        "scenes": [
            {
                "id": s.id,
                "scene_number": s.scene_number,
                "narration_text": s.narration_text,
                "visual_description": s.visual_description,
                "duration_seconds": s.duration_seconds,
                "transition": s.transition,
                "asset_id": s.asset_id,
                "asset_filename": asset_records[s.scene_number].filename if s.scene_number in asset_records else None,
                "voiceover_id": s.voiceover_asset_id,
                "caption_data": json.loads(s.caption_data_json),
            }
            for s in created_scenes
        ],
    }

    # Save to project folder and root data/projects
    p_json_1 = proj_dir / "project.json"
    p_json_2 = settings.PROJECTS_DIR / "3_forbidden_places_on_earth.json"
    p_json_1.write_text(json.dumps(project_dict, indent=2), encoding="utf-8")
    p_json_2.write_text(json.dumps(project_dict, indent=2), encoding="utf-8")
    logger.info("✓ Saved project JSON configurations to:")
    logger.info("  • %s", p_json_1)
    logger.info("  • %s", p_json_2)

    # Step 7: Create Render Job & Execute FFmpeg Master Assembly
    logger.info("\nStarting FFmpeg Master Render Pipeline...")
    render_settings = {
        "resolution_w": RESOLUTION_W,
        "resolution_h": RESOLUTION_H,
        "fps": FPS,
        "quality": "high",
        "output_format": "mp4",
    }

    job = Job(
        id=uuid.uuid4().hex,
        project_id=project.id,
        job_type="render",
        status="pending",
        current_stage="initializing",
        result_json=json.dumps(render_settings),
    )
    db.add(job)
    project.status = "rendering"
    db.commit()
    db.refresh(job)

    logger.info("Spawned render Job %s. Executing assembly...", job.id)
    success, error_msg = orchestrator._execute_render_job(job, db)

    if not success:
        logger.error("Render failed: %s (Error: %s)", job.error_message, error_msg)
        raise RuntimeError(f"Render job failed: {error_msg}")

    job.status = "completed"
    job.progress = 100.0
    job.current_stage = "Finished successfully"
    project.status = "completed"
    db.commit()

    # Step 8: Inspect and Validate Output Video
    job_result = json.loads(job.result_json) if job.result_json else {}
    master_path = Path(job_result.get("output_path", ""))

    logger.info("==================================================")
    logger.info("🎉 Master Vertical Video Render Completed Successfully!")
    logger.info("==================================================")
    logger.info("Master MP4 File: %s", master_path)
    logger.info("File Size: %d bytes (%.2f MB)", master_path.stat().st_size, master_path.stat().st_size / (1024*1024))

    # Probe final video with ffprobe
    probe = VideoEngine.probe_media(str(master_path))
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    logger.info("Duration: %.2f seconds", float(fmt.get("duration", 0)))
    logger.info("Dimensions: %sx%s (Vertical 9:16)", v_stream.get("width"), v_stream.get("height"))
    logger.info("Video Codec: %s @ %s fps", v_stream.get("codec_name"), eval(v_stream.get("r_frame_rate", "30/1")))
    logger.info("Audio Codec: %s @ %s Hz", a_stream.get("codec_name"), a_stream.get("sample_rate"))
    logger.info("Ready for preview and export!")

    db.close()

if __name__ == "__main__":
    main()
