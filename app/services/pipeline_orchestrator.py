"""
Production Pipeline Orchestrator for Shorts Studio.
Manages persistent background job execution, dependency resolution, retries, and media assembly.
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings
from app.database import SessionLocal
from app.models import Asset, Job, Project, Scene, Script
from app.services.video_engine import VideoEngine
from app.services.voice_engine import VoiceEngine

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Singleton background orchestrator that continuously processes queued jobs."""

    _instance: Optional["PipelineOrchestrator"] = None
    _worker_thread: Optional[threading.Thread] = None
    _running: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def start(self):
        """Start the background orchestrator loop."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="PipelineWorker")
        self._worker_thread.start()
        logger.info("Pipeline Orchestrator worker started")

    def stop(self):
        """Signal worker thread to stop."""
        self._running = False
        logger.info("Pipeline Orchestrator worker stopping")

    def _worker_loop(self):
        """Poll the database for pending jobs and execute them."""
        while self._running:
            try:
                self._process_next_job()
            except Exception as e:
                logger.exception("Error in orchestrator loop: %s", e)
            time.sleep(1.5)

    def _process_next_job(self):
        db = SessionLocal()
        try:
            # Pick oldest pending or queued job
            job = (
                db.query(Job)
                .filter(Job.status.in_(("pending", "queued")))
                .order_by(Job.created_at.asc())
                .first()
            )
            if not job:
                return

            # Mark as running
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.progress = 5.0
            job.current_stage = f"Starting {job.job_type}"
            db.commit()
            db.refresh(job)

            logger.info("Starting execution for Job %s (%s)", job.id[:8], job.job_type)

            success = False
            error_msg = None

            if job.job_type == "render":
                success, error_msg = self._execute_render_job(job, db)
            elif job.job_type == "script_generation":
                success, error_msg = self._execute_script_generation(job, db)
            elif job.job_type == "voiceover":
                success, error_msg = self._execute_voiceover_job(job, db)
            else:
                # Unknown job type
                success = True
                job.current_stage = "Completed generic job"

            # Check if cancelled while running
            db.refresh(job)
            if job.status == "cancelled":
                logger.info("Job %s was cancelled by user", job.id[:8])
                return

            if success:
                job.status = "completed"
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                job.current_stage = "Finished successfully"
                # Update project status if render job
                if job.job_type == "render":
                    project = db.query(Project).filter(Project.id == job.project_id).first()
                    if project:
                        project.status = "completed"
                logger.info("Job %s completed successfully", job.id[:8])
            else:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    job.status = "failed"
                    job.error_message = error_msg or "Execution failed"
                    job.current_stage = f"Failed (attempt {job.retry_count}/{job.max_retries})"
                else:
                    job.status = "failed"
                    job.error_message = f"Max retries exceeded: {error_msg}"
                logger.error("Job %s failed: %s", job.id[:8], error_msg)

            db.commit()

        finally:
            db.close()

    def _execute_render_job(self, job: Job, db) -> tuple[bool, Optional[str]]:
        """Assemble all scenes into an MP4 file."""
        project = db.query(Project).filter(Project.id == job.project_id).first()
        if not project:
            return False, "Project not found"

        scenes_db = (
            db.query(Scene)
            .filter(Scene.project_id == project.id)
            .order_by(Scene.scene_number.asc())
            .all()
        )
        if not scenes_db:
            return False, "Project has no scenes to render"

        settings_dict = {}
        if job.result_json:
            try:
                settings_dict = json.loads(job.result_json)
            except Exception:
                pass

        is_preview = settings_dict.get("is_preview", False)
        quality = settings_dict.get("quality", "high")
        res_w = settings_dict.get("resolution_w") or project.resolution_w or 1080
        res_h = settings_dict.get("resolution_h") or project.resolution_h or 1920
        fps = settings_dict.get("fps") or project.fps or 30

        # Output destination
        renders_dir = Path(settings.RENDERS_DIR) / project.id
        renders_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{'preview' if is_preview else 'final'}_{job.id[:8]}.mp4"
        output_file = renders_dir / filename

        # Prepare scene dictionaries with resolved asset paths
        scene_payloads = []
        for sc in scenes_db:
            asset_path = None
            if sc.asset_id:
                asset_rec = db.query(Asset).filter(Asset.id == sc.asset_id).first()
                if asset_rec and Path(asset_rec.file_path).exists():
                    asset_path = asset_rec.file_path

            vo_path = None
            if sc.voiceover_asset_id:
                vo_rec = db.query(Asset).filter(Asset.id == sc.voiceover_asset_id).first()
                if vo_rec and Path(vo_rec.file_path).exists():
                    vo_path = vo_rec.file_path

            scene_payloads.append({
                "scene_number": sc.scene_number,
                "duration_seconds": sc.duration_seconds,
                "narration_text": sc.narration_text,
                "visual_description": sc.visual_description,
                "transition": sc.transition,
                "asset_path": asset_path,
                "voiceover_path": vo_path,
            })

        # Progress tracking callback
        def on_progress(pct: float, stage: str):
            try:
                db_sub = SessionLocal()
                j = db_sub.query(Job).filter(Job.id == job.id).first()
                if j and j.status != "cancelled":
                    j.progress = round(pct, 1)
                    j.current_stage = stage
                    db_sub.commit()
                db_sub.close()
            except Exception:
                pass

        # Check subtitles file
        subtitles_file = None
        captions_query = [s for s in scenes_db if s.caption_data_json]
        if captions_query:
            # We can generate a temporary SRT file for rendering
            srt_path = Path(settings.CACHE_DIR) / f"captions_{project.id}.srt"
            try:
                from app.routes.captions import _generate_segments_from_scenes, _segments_to_srt
                segments = _generate_segments_from_scenes(scenes_db)
                if segments:
                    srt_content = _segments_to_srt(segments)
                    srt_path.write_text(srt_content, encoding="utf-8")
                    subtitles_file = srt_path
            except Exception as e:
                logger.warning("Could not create SRT for burn-in: %s", e)

        # Run VideoEngine assembly
        success = VideoEngine.render_project_video(
            project_id=project.id,
            scenes=scene_payloads,
            output_file=output_file,
            resolution_w=res_w,
            resolution_h=res_h,
            fps=fps,
            is_preview=is_preview,
            subtitles_file=subtitles_file,
            progress_callback=on_progress,
        )

        if success and output_file.exists():
            settings_dict["output_path"] = str(output_file)
            job.result_json = json.dumps(settings_dict)

            # Record Asset record for rendered video
            asset = Asset(
                project_id=project.id,
                filename=output_file.name,
                original_filename=output_file.name,
                file_path=str(output_file),
                asset_type="video",
                source="generated",
                mime_type="video/mp4",
                file_size_bytes=output_file.stat().st_size,
            )
            db.add(asset)
            db.commit()
            return True, None
        else:
            return False, "FFmpeg rendering failed or produced invalid output."

    def _execute_script_generation(self, job: Job, db) -> tuple[bool, Optional[str]]:
        """Generate high-retention script for short-form video."""
        project = db.query(Project).filter(Project.id == job.project_id).first()
        if not project:
            return False, "Project not found"

        topic = project.topic or project.name or "Interesting Facts"
        niche = project.niche or "general"
        tone = project.tone or "engaging"

        # High-retention short video templates by category
        templates = {
            "educational": (
                f"Did you know this mind-blowing truth about {topic}?",
                f"Most people have no idea, but scientists discovered something crazy about {topic}. In fact, when researchers examined this closely, the results completely changed our understanding.",
                f"Next time you encounter {topic}, remember this fact.",
                "Hit subscribe for more unbelievable facts every day!"
            ),
            "technology": (
                f"This AI breakthrough with {topic} is changing everything.",
                f"Tech giants didn't want this getting out, but new advancements in {topic} are moving 10 times faster than expected. The implications for everyday life are massive.",
                f"The future of {topic} is already here.",
                "Drop your thoughts in the comments and follow for daily tech!"
            ),
            "history": (
                f"The forgotten secret of {topic} that history books hide.",
                f"Centuries ago, an astonishing event involving {topic} took place. What historians uncovered in the archives stunned everyone who investigated the incident.",
                f"And that is the real, untold story of {topic}.",
                "Like and subscribe if you love uncovering historical mysteries!"
            ),
            "motivational": (
                f"If you're struggling today, stop scrolling and hear this about {topic}.",
                f"The biggest difference between those who succeed with {topic} and those who give up is simple: persistence when no one is watching.",
                f"Your potential with {topic} has no limits.",
                "Save this video for when you need a reminder, and follow for more!"
            ),
        }

        hook, body, conclusion, cta = templates.get(
            niche.lower(),
            (
                f"The #1 thing you need to know about {topic} right now.",
                f"Here is why {topic} is capturing everyone's attention. When you break down the facts, three key elements stand out immediately.",
                f"That is the core reason {topic} matters today.",
                "Follow for more daily insights and share this with a friend!"
            )
        )

        full_content = f"{hook}\n\n{body}\n\n{conclusion}\n\n{cta}"
        words = len(full_content.split())
        est_duration = round((words / 150.0) * 60, 1)

        script = Script(
            project_id=project.id,
            version=1,
            content=full_content,
            hook=hook,
            body=body,
            conclusion=conclusion,
            cta=cta,
            word_count=words,
            estimated_duration_seconds=est_duration,
            status="draft",
            is_approved=False,
        )
        db.add(script)
        db.commit()
        db.refresh(script)

        # Auto-create storyboard scenes from generated script
        from app.routes.scenes import scenes_from_script
        scenes_from_script(project.id, script.id, db)

        return True, None

    def _execute_voiceover_job(self, job: Job, db) -> tuple[bool, Optional[str]]:
        """Synthesize voiceovers for all scenes."""
        scenes = db.query(Scene).filter(Scene.project_id == job.project_id).all()
        if not scenes:
            return False, "No scenes found"

        assets_dir = Path(settings.PROJECTS_DIR) / job.project_id / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        for sc in scenes:
            if not sc.narration_text:
                continue
            vo_path = assets_dir / f"scene_{sc.scene_number}_vo.wav"
            ok = VoiceEngine.generate_voiceover(sc.narration_text, vo_path)
            if ok and vo_path.exists():
                asset = Asset(
                    project_id=job.project_id,
                    filename=vo_path.name,
                    file_path=str(vo_path),
                    asset_type="voiceover",
                    source="generated",
                    mime_type="audio/wav",
                    file_size_bytes=vo_path.stat().st_size,
                )
                db.add(asset)
                db.flush()
                sc.voiceover_asset_id = asset.id

        db.commit()
        return True, None


orchestrator = PipelineOrchestrator()
