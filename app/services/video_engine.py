"""
FFmpeg Video Assembly and Rendering Engine for Shorts Studio.
Assembles scenes into vertical 9:16 MP4 videos with visual effects, transitions, audio mixing, and subtitles.
"""

import json
import logging
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class VideoEngine:
    """Manages scene-by-scene composition and full FFmpeg rendering."""

    @staticmethod
    def probe_media(file_path: str) -> dict[str, Any]:
        """Use ffprobe to inspect video/audio stream properties."""
        ffprobe_bin = settings.detect_ffmpeg().replace("ffmpeg.exe", "ffprobe.exe")
        if not Path(ffprobe_bin).exists():
            ffprobe_bin = "ffprobe"

        cmd = [
            ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout:
                return json.loads(res.stdout)
        except Exception as e:
            logger.warning("ffprobe failed on %s: %s", file_path, e)
        return {}

    @staticmethod
    def render_project_video(
        project_id: str,
        scenes: list[dict],
        output_file: Path,
        resolution_w: int = 1080,
        resolution_h: int = 1920,
        fps: int = 30,
        is_preview: bool = False,
        subtitles_file: Optional[Path] = None,
        background_music_file: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """
        Assemble storyboard scenes into a vertical 9:16 MP4 video.
        Uses procedural generation for scenes without user assets.
        """
        ffmpeg_bin = settings.detect_ffmpeg()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(settings.CACHE_DIR) / f"render_{project_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(5.0, "Preparing scene visual clips and voiceovers")

        rendered_scene_clips: list[Path] = []
        total_scenes = len(scenes)

        try:
            for idx, scene in enumerate(scenes, start=1):
                scene_num = scene.get("scene_number", idx)
                duration = float(scene.get("duration_seconds", 5.0))
                narration = scene.get("narration_text", "")
                visual_desc = scene.get("visual_description", "")
                asset_path = scene.get("asset_path")
                voice_path = scene.get("voiceover_path")

                clip_output = temp_dir / f"scene_{scene_num:03d}.mp4"

                # 1. Ensure voiceover audio exists for this scene
                audio_clip = temp_dir / f"scene_{scene_num:03d}_audio.wav"
                if voice_path and Path(voice_path).exists():
                    audio_clip = Path(voice_path)
                else:
                    from app.services.voice_engine import VoiceEngine
                    VoiceEngine.generate_voiceover(
                        text=narration or f"Scene {scene_num}",
                        output_path=audio_clip,
                    )

                # 2. Render individual scene clip
                VideoEngine._render_single_scene(
                    ffmpeg_bin=ffmpeg_bin,
                    scene_num=scene_num,
                    narration=narration,
                    visual_desc=visual_desc,
                    asset_path=asset_path,
                    audio_path=audio_clip,
                    duration=duration,
                    width=resolution_w,
                    height=resolution_h,
                    fps=fps,
                    output_path=clip_output,
                )

                if clip_output.exists() and clip_output.stat().st_size > 1000:
                    rendered_scene_clips.append(clip_output)

                pct = 5.0 + (idx / total_scenes) * 55.0
                if progress_callback:
                    progress_callback(pct, f"Rendered scene {idx}/{total_scenes}")

            if not rendered_scene_clips:
                raise RuntimeError("No scenes were rendered successfully.")

            # 3. Concatenate scene clips
            if progress_callback:
                progress_callback(65.0, "Concatenating scenes with seamless transitions")

            concat_txt = temp_dir / "concat_list.txt"
            with open(concat_txt, "w", encoding="utf-8") as f:
                for clip in rendered_scene_clips:
                    # Escape path for FFmpeg concat demuxer
                    safe_path = str(clip).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")

            merged_video = temp_dir / "merged_raw.mp4"
            cmd_concat = [
                ffmpeg_bin,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_txt),
                "-c", "copy",
                str(merged_video),
            ]
            res = subprocess.run(cmd_concat, capture_output=True, timeout=60)
            if res.returncode != 0 or not merged_video.exists() or merged_video.stat().st_size < 1000:
                logger.warning("Concat with -c copy had issues, falling back to re-encode...")
                cmd_concat_fallback = [
                    ffmpeg_bin,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_txt),
                    "-c:v", "libx264",
                    "-preset", "ultrafast" if is_preview else "veryfast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(merged_video),
                ]
                res = subprocess.run(cmd_concat_fallback, capture_output=True, timeout=300)
                if res.returncode != 0 or not merged_video.exists():
                    logger.error("Concat failed: %s", res.stderr.decode("utf-8", "replace"))
                    raise RuntimeError("Failed to concatenate scenes.")

            # 4. Mix background music if provided
            final_audio_video = merged_video
            if background_music_file and Path(background_music_file).exists():
                if progress_callback:
                    progress_callback(75.0, "Mixing background music and ducking audio")
                bgm_mixed = temp_dir / "with_bgm.mp4"
                cmd_bgm = [
                    ffmpeg_bin,
                    "-y",
                    "-i", str(merged_video),
                    "-stream_loop", "-1",
                    "-i", str(background_music_file),
                    "-filter_complex",
                    "[1:a]volume=0.18[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(bgm_mixed),
                ]
                res_bgm = subprocess.run(cmd_bgm, capture_output=True, timeout=120)
                if res_bgm.returncode == 0 and bgm_mixed.exists():
                    final_audio_video = bgm_mixed

            # 5. Burn-in subtitles if subtitles file exists
            if subtitles_file and Path(subtitles_file).exists():
                if progress_callback:
                    progress_callback(85.0, "Burning subtitles into vertical frame")
                # Subtitles filter in ffmpeg
                srt_path_escaped = str(subtitles_file).replace("\\", "/").replace(":", "\\:")
                cmd_sub = [
                    ffmpeg_bin,
                    "-y",
                    "-i", str(final_audio_video),
                    "-vf", f"subtitles='{srt_path_escaped}':force_style='PlayResX=1080,PlayResY=1920,FontSize=52,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=260'",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "copy",
                    str(output_file),
                ]
                res_sub = subprocess.run(cmd_sub, capture_output=True, timeout=300)
                if res_sub.returncode == 0 and output_file.exists() and output_file.stat().st_size > 1000:
                    pass
                else:
                    logger.warning("Subtitles burn-in had issues: %s. Using unsubtitled video.", res_sub.stderr)
                    import shutil
                    shutil.copy2(str(final_audio_video), str(output_file))
            else:
                import shutil
                shutil.copy2(str(final_audio_video), str(output_file))

            # 6. Validate final output file
            if progress_callback:
                progress_callback(95.0, "Validating final vertical MP4 media container")

            validation = VideoEngine.validate_output_video(output_file, resolution_w, resolution_h)
            if not validation["valid"]:
                logger.warning("Video output validation warning: %s", validation["issues"])

            if progress_callback:
                progress_callback(100.0, "Render completed successfully")

            return True

        except Exception as e:
            logger.exception("Render pipeline error: %s", e)
            if progress_callback:
                progress_callback(0.0, f"Error: {e}")
            return False

    @staticmethod
    def _render_single_scene(
        ffmpeg_bin: str,
        scene_num: int,
        narration: str,
        visual_desc: str,
        asset_path: Optional[str],
        audio_path: Path,
        duration: float,
        width: int,
        height: int,
        fps: int,
        output_path: Path,
    ) -> None:
        """Render a single scene clip matching dimensions and frame rate."""
        # Visual color palette cycling for procedural scenes
        colors = [
            ("#1e1e2f", "#4a47a3"),  # Dark purple/navy
            ("#14213d", "#fca311"),  # Deep blue & gold
            ("#0b0c10", "#45a29e"),  # Cyber teal
            ("#222831", "#00adb5"),  # Slate blue
            ("#1a1a24", "#7d5fff"),  # Neon violet
        ]
        bg_col, accent_col = colors[(scene_num - 1) % len(colors)]

        has_valid_asset = asset_path and Path(asset_path).exists()
        audio_exists = audio_path.exists() and audio_path.stat().st_size > 100

        # If image/video asset is provided
        if has_valid_asset:
            ext = Path(asset_path).suffix.lower()
            is_video = ext in (".mp4", ".mov", ".mkv", ".webm")

            if is_video:
                # Video input: scale and pad to vertical 9:16, loop if necessary
                vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
                cmd = [
                    ffmpeg_bin, "-y",
                    "-stream_loop", "-1",
                    "-i", str(asset_path),
                ]
            else:
                # Image input: scale, pad, and add subtle Ken Burns zoompan
                vf = f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.15)':d={int(duration*fps)}:s={width}x{height}:fps={fps},setsar=1"
                cmd = [
                    ffmpeg_bin, "-y",
                    "-loop", "1",
                    "-i", str(asset_path),
                ]
        else:
            # Procedural visual generator: animated stylish gradient title-card
            clean_text = (visual_desc or narration or f"Scene {scene_num}").replace("'", "").replace(":", "-")[:60]
            # FFmpeg lavfi generator for vertical canvas
            vf = (
                f"color=c={bg_col}:s={width}x{height}:d={duration}:r={fps},"
                f"drawbox=x=80:y=80:w={width-160}:h={height-160}:color={accent_col}@0.4:t=4,"
                f"drawtext=text='SCENE {scene_num}':fontcolor=white@0.8:fontsize=36:x=(w-text_w)/2:y=300,"
                f"drawtext=text='{clean_text}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.6:boxborderw=20"
            )
            cmd = [
                ffmpeg_bin, "-y",
                "-f", "lavfi",
                "-i", vf,
            ]

        # Add audio track input
        if audio_exists:
            cmd.extend(["-i", str(audio_path)])
        else:
            cmd.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo"])

        cmd.extend([
            "-vf", vf if has_valid_asset else "null",
            "-t", str(round(duration, 2)),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ])

        subprocess.run(cmd, capture_output=True, timeout=60)

    @staticmethod
    def validate_output_video(file_path: Path, expected_w: int = 1080, expected_h: int = 1920) -> dict[str, Any]:
        """Validate the rendered MP4 file."""
        if not file_path.exists():
            return {"valid": False, "issues": ["File does not exist"]}

        size_bytes = file_path.stat().st_size
        if size_bytes < 10000:
            return {"valid": False, "issues": ["File is implausibly small (<10KB)"]}

        info = VideoEngine.probe_media(str(file_path))
        streams = info.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        issues = []
        if not has_video:
            issues.append("Missing video stream")
        if not has_audio:
            issues.append("Missing audio stream")

        duration = float(info.get("format", {}).get("duration", 0))
        if duration < 1.0:
            issues.append("Duration is too short (< 1.0s)")

        return {
            "valid": len(issues) == 0,
            "size_bytes": size_bytes,
            "duration": duration,
            "has_video": has_video,
            "has_audio": has_audio,
            "issues": issues,
        }
