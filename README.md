# 🎬 Shorts Studio — Complete AI Video Production Pipeline

**Shorts Studio** is a complete, local-first production studio that transforms a simple video concept into a finished, polished vertical video (9:16) ready for YouTube Shorts, TikTok, and Instagram Reels.

Built with a high-performance **FastAPI** backend, **SQLite** persistent metadata, a **portable FFmpeg 9.0 media engine**, and a responsive **dark-themed Single Page Application (SPA)** that runs directly in your browser without requiring Node.js or npm build steps.

---

## 🌟 Key Highlights

- **Zero-Cost & 100% Offline Capable**: Works out-of-the-box without paid AI subscriptions using built-in procedural visual generation and local Windows SAPI speech synthesis.
- **Portable FFmpeg Included**: Pre-configured static build of FFmpeg 9.0 in `bin/` (`ffmpeg.exe` and `ffprobe.exe`) with H.264, AAC, and subtitle rendering support.
- **Vertical 9:16 Video Master**: Outputs crisp 1080×1920 (or 540×960 fast preview) MP4 video at 30 fps.
- **Complete End-to-End Pipeline**:
  `IDEA → SCRIPT → STORYBOARD → VOICEOVER → VISUALS → ASSEMBLY → CAPTIONS → RENDERING → QC → EXPORT`
- **Persistent Background Orchestrator**: Runs rendering and synthesis jobs with real progress tracking, recovery on restart, and bounded retries.
- **Automated Quality Control**: Evaluates scene timings, approved scripts, vertical aspect ratio, and audio streams before export.

---

## 🚀 Quick Start (Beginner Friendly)

### 1. Requirements
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.11+ installed

### 2. Launching the Studio
You can start the studio in one double-click or via terminal:

#### Option A: One-Click Batch Launcher
Double-click `launch.bat` in the project directory.

#### Option B: PowerShell
```powershell
.\launch.ps1
```

#### Option C: Manual Command
```powershell
.\venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once started, open your web browser at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧭 Application Modules & Panels

The left sidebar gives you direct access to all 14 integrated studio sections:

| # | Panel | Purpose & Implemented Capabilities |
|---|---|---|
| 1 | **Dashboard** | Studio status overview, active jobs tracker, system diagnostics (FFmpeg status), and recent projects list. |
| 2 | **New Project** | Quick-start wizard for topics (Educational, Tech, History, Story, Motivational), tone, duration slider (15–180s), and presets. |
| 3 | **Project Library** | Project cards with status badges (Draft, Production, Rendering, Completed), search, duplicate, and deletion. |
| 4 | **Script Editor** | Structured hook/body/conclusion/CTA editor, live word count, narration duration estimator (150 wpm), version history, and approval gates. |
| 5 | **Storyboard & Scenes** | Scene cards with visual descriptions, durations, transitions (crossfade, fade, wipe, cut), reordering, and auto-split from script. |
| 6 | **Voiceover Studio** | Scene-by-scene audio generator with Windows SAPI synthesizer fallback, external TTS connector, and audio import. |
| 7 | **Visual Assets** | File uploader with automatic MIME detection (image/video/audio), scene assignment, and trash recovery. |
| 8 | **Video Editor & Timeline** | Multi-track timeline visualizer (Visuals, Voiceover, Captions), live monitor preview player, and render trigger buttons. |
| 9 | **Captions & Subtitles** | Phrase-level caption generator, visual 9:16 safe area overlay, font/size/color styling controls, and SRT export. |
| 10 | **Render Queue** | Live background job status monitor, progress bar, current stage tracker, cancellation, and retry controls. |
| 11 | **Quality Control** | Automated 6-point pre-flight checks with scores, pass/warning/fail badges, and actionable fix suggestions. |
| 12 | **Export Center** | Finished vertical MP4 player, stream codec specs (libx264, aac), SRT subtitle downloader, and platform presets. |
| 13 | **Settings & Providers** | API key configurations for OpenAI, Anthropic, ElevenLabs, Pexels, and Pixabay, plus system path detectors. |
| 14 | **Logs & Diagnostics** | Real-time console log viewer with INFO, WARNING, and ERROR filtering and auto-refresh stream. |

---

## 🛠️ Offline vs. AI Provider Setup

Shorts Studio is designed so that a beginner can run the full pipeline without spending money or setting up cloud accounts.

### 1. Default Offline Mode (No Keys Required)
- **Scripts**: Written directly or generated using high-retention structural templates.
- **Voiceover**: Rendered directly via local Windows Speech Synthesis (SAPI) into genuine audio tracks.
- **Visuals**: Dynamic procedural styling, color-cycled typography canvas, Ken Burns zoom effects, or imported local files.
- **Assembly**: Powered by the bundled portable FFmpeg binary in `bin/ffmpeg.exe`.

### 2. Connecting External Providers (Optional)
To connect premium AI providers, go to the **Settings** page in the studio or configure `.env`:

- **OpenAI (`OPENAI_API_KEY`)**: For GPT-4o automated scriptwriting and DALL-E 3 image generation.
- **Anthropic (`ANTHROPIC_API_KEY`)**: For Claude 3.5 research briefs and script revision.
- **ElevenLabs (`ELEVENLABS_API_KEY`)**: For expressive neural voices.
- **Pexels (`PEXELS_API_KEY`)**: For searching and downloading free stock vertical footage.
- **Pixabay (`PIXABAY_API_KEY`)**: For royalty-free background music and audio effects.

---

## 🎬 Example Project Included

The studio comes pre-populated with a complete example project:
- **Title**: *Top 3 Secrets of the Deep Ocean*
- **Scenes**: 5 complete scenes with narration, procedural graphics, and voiceovers.
- **Rendered Output**: Playable vertical 1080×1920 MP4 file ready to inspect under `data/renders/`.

To inspect it, launch the studio and click on the project in the **Dashboard** or **Project Library**!

---

## 🧪 Automated Testing

Shorts Studio includes a full end-to-end automated test suite:

```powershell
.\venv\Scripts\pytest -v tests/test_full_pipeline.py
```

### Verified Test Results:
```text
tests/test_full_pipeline.py::test_health_check PASSED                    [ 14%]
tests/test_full_pipeline.py::test_project_crud PASSED                    [ 28%]
tests/test_full_pipeline.py::test_script_and_scenes_flow PASSED          [ 42%]
tests/test_full_pipeline.py::test_captions_generation_and_export PASSED  [ 57%]
tests/test_full_pipeline.py::test_quality_checks PASSED                  [ 71%]
tests/test_full_pipeline.py::test_voiceover_synthesis PASSED             [ 85%]
tests/test_full_pipeline.py::test_ffmpeg_video_assembly_real PASSED      [100%]
======================= 7 passed in 16.91s ========================
```

---

## ❓ Troubleshooting Guide

### 1. "Port 8000 already in use"
If another program is using port 8000, specify a different port:
```powershell
.\venv\Scripts\python -m uvicorn app.main:app --port 8080
```

### 2. "FFmpeg not detected"
Shorts Studio automatically checks `bin/ffmpeg.exe`. If you want to use your own system FFmpeg, ensure it is added to your Windows `PATH`, or set `FFMPEG_PATH="C:\path\to\ffmpeg.exe"` in `.env`.

### 3. Voiceover sounds robotic
Windows default speech voices depend on your Windows Language settings. You can install higher-quality natural voices in **Windows Settings → Time & Language → Speech → Add voices**, or configure an **ElevenLabs API Key** in Settings.

### 4. Background task interrupted
If you close the application during rendering, the persistent pipeline orchestrator detects interrupted jobs on the next launch and allows you to retry or resume with one click in the **Render Queue**.

---

## 📁 Directory Structure

```text
ShortsStudio/
├── app/
│   ├── routes/              # FastAPI API routes (projects, scripts, scenes, render, etc.)
│   ├── services/            # Core engines (video_engine.py, voice_engine.py, orchestrator.py)
│   ├── config.py            # Central configuration and path auto-detection
│   ├── database.py          # SQLite engine and session factory
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── logging_config.py    # Rotating file & console logging
│   └── main.py              # Application entry point & lifespan
├── bin/
│   ├── ffmpeg.exe           # Portable static FFmpeg 9.0 executable
│   └── ffprobe.exe          # Portable static FFprobe media inspection tool
├── data/
│   ├── assets/              # Stored media assets
│   ├── cache/               # Temporary render scratch directory
│   ├── logs/                # Rotating server logs (shorts_studio.log)
│   ├── projects/            # Project-specific assets and storyboards
│   ├── renders/             # Final exported vertical MP4 videos
│   └── shorts_studio.db     # SQLite database
├── frontend/
│   ├── css/
│   │   └── main.css         # Complete dark theme styling
│   ├── js/
│   │   ├── pages/           # Dynamic ES modules for all 14 studio panels
│   │   └── app.js           # Client router, toasts, modal manager, and API client
│   └── index.html           # Main Single Page Application shell
├── tests/
│   └── test_full_pipeline.py # End-to-end automated test suite
├── launch.bat               # Windows one-click batch launcher
├── launch.ps1               # PowerShell launcher
├── requirements.txt         # Pinned Python package dependencies
├── .env.example             # Example configuration
└── README.md                # Documentation & User Guide
```
