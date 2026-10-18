"""
Provider-independent Voiceover Synthesis Engine for Shorts Studio.
Supports external providers (ElevenLabs, OpenAI TTS) with local Windows SAPI fallback.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class VoiceEngine:
    """Manages text-to-speech voice generation and audio file export."""

    @staticmethod
    def generate_voiceover(
        text: str,
        output_path: Path,
        provider: Optional[str] = None,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> bool:
        """
        Synthesize narration speech from text.
        Tries external provider if configured; falls back to Windows SAPI speech synthesizer.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        selected_provider = (provider or settings.TTS_PROVIDER or "none").lower()

        # 1. External: ElevenLabs if configured
        if selected_provider == "elevenlabs" and os.environ.get("ELEVENLABS_API_KEY"):
            try:
                import httpx
                api_key = os.environ.get("ELEVENLABS_API_KEY")
                voice = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel default
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                payload = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        output_path.write_bytes(resp.content)
                        logger.info("Generated voiceover via ElevenLabs: %s", output_path)
                        return True
            except Exception as e:
                logger.warning("ElevenLabs TTS failed: %s. Falling back to local synthesizer.", e)

        # 2. Local Fallback: Windows SAPI via PowerShell
        success = VoiceEngine._generate_local_sapi(text, output_path, speed)
        if success:
            return True

        # 3. Silent audio fallback via FFmpeg if TTS is completely unavailable
        return VoiceEngine._generate_silence_fallback(output_path, duration=max(2.0, len(text.split()) / 2.5))

    @staticmethod
    def _generate_local_sapi(text: str, output_path: Path, speed: float = 1.0) -> bool:
        """Use Windows SAPI SpeechSynthesizer to generate a real WAV audio file."""
        wav_path = output_path.with_suffix(".wav")
        # Sanitize text for PowerShell string
        safe_text = text.replace('"', '""').replace("'", "''").replace("`", "")

        # SAPI Rate ranges from -10 to 10. Map 1.0 -> 0, 1.2 -> 2, 0.8 -> -2
        rate = int(round((speed - 1.0) * 10))
        rate = max(-10, min(10, rate))

        ps_script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = {rate}
$synth.SetOutputToWaveFile("{wav_path}")
$synth.Speak("{safe_text}")
$synth.Dispose()
"""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode == 0 and wav_path.exists() and wav_path.stat().st_size > 500:
                # If target was mp3, convert or keep wav
                if output_path.suffix.lower() == ".mp3":
                    ffmpeg_bin = settings.detect_ffmpeg()
                    cmd = [ffmpeg_bin, "-y", "-i", str(wav_path), "-b:a", "192k", str(output_path)]
                    conv_res = subprocess.run(cmd, capture_output=True, timeout=20)
                    if conv_res.returncode == 0 and output_path.exists():
                        try:
                            wav_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        logger.info("Local SAPI voiceover generated (MP3): %s", output_path)
                        return True
                logger.info("Local SAPI voiceover generated (WAV): %s", wav_path)
                return True
            else:
                logger.warning("PowerShell SAPI returned code %d: %s", res.returncode, res.stderr)
        except Exception as e:
            logger.warning("Windows SAPI error: %s", e)

        return False

    @staticmethod
    def _generate_silence_fallback(output_path: Path, duration: float = 3.0) -> bool:
        """Generate a clean audio track with soft ambient tone using FFmpeg."""
        ffmpeg_bin = settings.detect_ffmpeg()
        try:
            # Generate a very soft subtle sine or silence track
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(round(duration, 2)),
                "-c:a", "aac",
                str(output_path),
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=15)
            return res.returncode == 0 and output_path.exists()
        except Exception as e:
            logger.error("Silence fallback generation failed: %s", e)
            return False
