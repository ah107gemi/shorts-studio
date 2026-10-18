"""
Initializes an exemplary starter project with script, scenes, audio, and a rendered video.
"""

import json
from pathlib import Path

from app.config import settings
from app.database import Base, SessionLocal, init_db
from app.models import Asset, Job, Project, Scene, Script
from app.services.video_engine import VideoEngine
from app.services.voice_engine import VoiceEngine


def create_demo_project():
    init_db()
    db = SessionLocal()

    existing = db.query(Project).filter(Project.name == "Top 3 Secrets of the Deep Ocean").first()
    if existing:
        print("Example project already exists.")
        db.close()
        return

    print("Creating example project: 'Top 3 Secrets of the Deep Ocean'...")
    project = Project(
        name="Top 3 Secrets of the Deep Ocean",
        topic="Deep Ocean Mysteries",
        niche="educational",
        target_audience="General Audience",
        language="en",
        target_duration_seconds=30,
        tone="mysterious",
        style="cinematic",
        platform="youtube_shorts",
        visual_style="dark_blue_abyss",
        resolution_w=1080,
        resolution_h=1920,
        fps=30,
        status="completed",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 1. Script
    hook = "Over 80% of our ocean remains completely unmapped and unexplored."
    body = "Deep in the Mariana Trench, hydrothermal vents spew water at 700 degrees Fahrenheit without boiling due to crushing pressure. Strange bioluminescent creatures thrive here in total darkness."
    conclusion = "We know more about the surface of Mars than the bottom of our own seas."
    cta = "Follow Shorts Studio for more unexplained mysteries!"
    content = f"{hook}\n\n{body}\n\n{conclusion}\n\n{cta}"

    script = Script(
        project_id=project.id,
        version=1,
        content=content,
        hook=hook,
        body=body,
        conclusion=conclusion,
        cta=cta,
        word_count=len(content.split()),
        estimated_duration_seconds=26.0,
        status="approved",
        is_approved=True,
    )
    db.add(script)
    db.commit()
    db.refresh(script)

    # 2. Scenes
    scene_defs = [
        (1, hook, "The Uncharted Ocean Abyss", 5.0),
        (2, "Deep in the Mariana Trench, water reaches 700 degrees without boiling.", "Mariana Trench Hydrothermal Vents", 6.5),
        (3, "Bioluminescent creatures thrive in total crushing darkness.", "Glowing Deep Sea Bioluminescence", 6.5),
        (4, conclusion, "Earth Ocean vs Mars Comparison", 5.5),
        (5, cta, "Call to Action Channel Subscribe", 4.0),
    ]

    scenes_db = []
    assets_dir = Path(settings.PROJECTS_DIR) / project.id / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for num, narr, vis, dur in scene_defs:
        vo_path = assets_dir / f"scene_{num}_vo.wav"
        VoiceEngine.generate_voiceover(narr, vo_path)

        vo_asset = None
        if vo_path.exists():
            vo_asset = Asset(
                project_id=project.id,
                filename=vo_path.name,
                file_path=str(vo_path),
                asset_type="voiceover",
                source="generated",
                mime_type="audio/wav",
                file_size_bytes=vo_path.stat().st_size,
            )
            db.add(vo_asset)
            db.flush()

        sc = Scene(
            project_id=project.id,
            script_id=script.id,
            scene_number=num,
            narration_text=narr,
            visual_description=vis,
            duration_seconds=dur,
            voiceover_asset_id=vo_asset.id if vo_asset else None,
        )
        db.add(sc)
        scenes_db.append(sc)

    db.commit()

    # 3. Render Sample Video
    renders_dir = Path(settings.RENDERS_DIR) / project.id
    renders_dir.mkdir(parents=True, exist_ok=True)
    sample_mp4 = renders_dir / "final_demo_short.mp4"

    print("Rendering sample vertical MP4 video...")
    scene_payloads = []
    for sc in scenes_db:
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
            "transition": "crossfade",
            "voiceover_path": vo_path,
        })

    ok = VideoEngine.render_project_video(
        project_id=project.id,
        scenes=scene_payloads,
        output_file=sample_mp4,
        resolution_w=1080,
        resolution_h=1920,
        fps=30,
        is_preview=False,
    )

    if ok and sample_mp4.exists():
        video_asset = Asset(
            project_id=project.id,
            filename=sample_mp4.name,
            file_path=str(sample_mp4),
            asset_type="video",
            source="generated",
            mime_type="video/mp4",
            file_size_bytes=sample_mp4.stat().st_size,
        )
        db.add(video_asset)

        # Create completed Job record
        job = Job(
            project_id=project.id,
            job_type="render",
            status="completed",
            progress=100.0,
            current_stage="Finished successfully",
            result_json=json.dumps({"output_path": str(sample_mp4)}),
        )
        db.add(job)
        db.commit()
        print(f"Sample project rendered: {sample_mp4} ({sample_mp4.stat().st_size} bytes)")

    db.close()


if __name__ == "__main__":
    create_demo_project()
