# PROJECT MASTER BRIEF
# SHORTS STUDIO — COMPLETE AI VIDEO PRODUCTION PIPELINE

## 1. Project Overview

**Project name:** Shorts Studio

**Project type:** Local AI-assisted video production application.

**Primary objective:** Build an application that automates as much of the YouTube Shorts production process as possible, transforming a simple video idea into a finished, high-quality vertical video ready for manual upload to YouTube.

**Development environment:** Google Antigravity.

**Current status:** Antigravity has completed its initial implementation. The actual implementation, functionality, launch status, errors, and end-to-end video production capability have not yet been independently verified.

**Developer experience:** Beginner. Development guidance should be understandable, but the application itself should be implemented professionally.

**Hardware considerations:** Prefer an efficient architecture that works on ordinary consumer hardware and does not require a powerful GPU.

**Budget philosophy:** Prioritize free and low-cost tools. Do not assume that a Google AI subscription includes API credits, access to every external AI model, or unlimited generation.

## 2. The Core Idea

Shorts Studio is intended to become a local production studio that automates the following workflow:

**VIDEO IDEA → RESEARCH → SCRIPT GENERATION → SCRIPT APPROVAL → STORYBOARD → VOICEOVER → VISUAL ASSETS → VIDEO ASSEMBLY → CAPTIONS → AUDIO MIXING → FINAL RENDER → QUALITY CONTROL → EXPORT**

The ultimate goal is to let the user provide a topic, configure a few preferences, and have Shorts Studio manage the production stages with as little manual intervention as practical.

The application must support both:
- Automated production, where the application progresses through configured stages.
- Assisted production, where the user reviews and approves important stages.

The finished result must be an actual playable video file, not merely a project preview or an attractive interface.

## 3. Primary Requirements

### A. Project Management
- Create, save, reopen, and organize video projects.
- Store scripts, settings, storyboards, audio, images, footage, and renders.
- Preserve project progress across application restarts.
- Allow editing and regenerating individual stages without rebuilding everything.

### B. AI Scriptwriting
- Generate scripts from user-provided topics.
- Create strong opening hooks and engaging narrative structures.
- Support different niches, tones, languages, and target audiences.
- Divide scripts into scenes with narration, visual instructions, and estimated durations.
- Allow manual editing, alternative versions, and approval before production.

### C. Research
- Accept manually provided research and reference URLs.
- Integrate a search provider where available.
- Retain source links and distinguish verified information from assumptions.
- Never invent citations, facts, or quotations.

### D. Voiceover
- Generate narration through configurable text-to-speech providers.
- Support imported audio and local alternatives where practical.
- Allow voice selection, speed adjustments, previews, and regeneration of individual lines.
- Reuse existing audio when it has not changed.

### E. Visual Assets
- Import user-owned images and video footage.
- Support permitted stock-media sources.
- Integrate image or video generation APIs when configured.
- Provide fallback graphics and title cards when generation services are unavailable.
- Keep track of asset origins, licenses, and attribution information where available.

### F. Video Assembly
- Use FFmpeg or another suitable media-processing solution.
- Produce vertical 9:16 videos, targeting 1080 × 1920 where practical.
- Combine narration, images, video clips, captions, transitions, and background music.
- Support scene timing, basic zoom and pan effects, text overlays, and audio fades.
- Export playable MP4 files using widely supported codecs.

### G. Captions
- Generate captions from the narration or approved script.
- Synchronize captions using speech alignment or recognition when available.
- Allow manual corrections and styling.
- Support burned-in subtitles and SRT export.

### H. Pipeline Automation
- Execute production stages in the correct dependency order.
- Track real job status and progress.
- Handle errors and retry recoverable failures.
- Resume interrupted work.
- Cache completed results to avoid unnecessary regeneration.
- Allow scene-specific regeneration.
- Require confirmation for unexpected paid operations, destructive actions, or external publishing.

### I. Quality Control
- Detect missing assets and invalid files.
- Check video duration, aspect ratio, resolution, and media streams.
- Check caption timing and audio issues where possible.
- Validate the final render.
- Produce a quality report and clearly identify warnings or failures.

### J. Export
- Save finished videos locally.
- Provide export settings suitable for YouTube Shorts.
- Generate a production report containing output details and relevant asset sources.
- Do not automatically publish videos online in the initial version.

## 4. Technical Direction

Use the architecture already present in the existing application if it is suitable.

If a rebuild or major architectural change is proposed, explain why before proceeding.

Preferred technologies, if not already implemented:
- Frontend: React and TypeScript.
- Backend: Python and FastAPI.
- Project database: SQLite.
- Media processing: FFmpeg.
- AI integrations: Modular provider adapters.
- Configuration: Environment variables and local settings.
- Testing: Automated tests and end-to-end production tests.

Keep the application modular so that different AI providers can be replaced without rewriting the entire system.

The application should remain useful without paid AI services through manual script entry, imported assets, local processing, and documented fallbacks.

## 5. Important Constraints

1. Do not assume that Antigravity's subscription provides API access to third-party AI services.
2. Do not require paid services for the basic application to launch.
3. Do not store API keys in source code or expose them in logs.
4. Do not claim a feature works until it has been implemented and tested.
5. Do not substitute mock data for real functionality.
6. Do not overwrite existing work or start over unnecessarily.
7. Do not install unexpected dependencies or perform destructive operations without appropriate approval.
8. Do not automatically publish videos or incur unexpected costs.
9. Keep the project compatible with the user's available hardware wherever practical.
10. Prioritize reliability and a functioning end-to-end workflow over advanced features and visual polish.

## 6. Development Priorities

Follow this order:

**Priority 1 — Inspect and verify**
Inspect the existing application, identify its technologies, inspect its files, determine how it launches, and identify what actually works.

**Priority 2 — Establish a reliable foundation**
Ensure the application launches, projects can be saved, settings persist, and errors are reported clearly.

**Priority 3 — Produce a real video**
Implement and verify the basic workflow using a test project, sample assets, imported narration, captions, FFmpeg assembly, and a playable MP4.

**Priority 4 — Integrate AI**
Add script generation, research, voice generation, and visual sourcing through configurable providers.

**Priority 5 — Automate the pipeline**
Connect the stages into a persistent workflow with progress tracking, caching, retries, and recovery.

**Priority 6 — Improve production quality**
Add better scene management, captions, transitions, audio mixing, quality checks, and export options.

**Priority 7 — Optional expansion**
Consider batch production, templates, scheduling, publishing integrations, and advanced analytics only after the core pipeline works reliably.

## 7. Definition of Success

The project is successful when the user can:

1. Launch Shorts Studio locally.
2. Create a new video project.
3. Enter a topic or provide a script.
4. Generate or import narration and visuals.
5. Organize scenes and captions.
6. Assemble the video automatically.
7. Render a playable vertical MP4.
8. Run quality checks.
9. Locate the finished video and its production report.
10. Reopen the project later without losing progress.

At least one complete test video must be produced and validated before declaring the core pipeline operational.

## 8. Collaboration Between Gemini, Antigravity, and ChatGPT

Gemini and Antigravity are responsible for examining the existing codebase, implementing features, running commands, testing the application, and fixing implementation errors.

ChatGPT is a second assistant that can help with architecture decisions, project planning, debugging, code review, troubleshooting, and improving instructions.

Maintain a clear project status that can be shared between assistants. Do not assume either assistant can automatically see the other's conversations or actions.

When useful, provide concise progress reports containing:
- Current project status.
- Files or modules changed.
- Features implemented.
- Tests executed and their actual results.
- Known bugs and limitations.
- Required dependencies or API credentials.
- The next recommended task.

## 9. Immediate Instruction

The initial application has already been generated in Antigravity.

**Do not recreate Shorts Studio from scratch.**

First inspect the existing workspace and report:

1. What technologies and architecture are actually present.
2. How to launch the application.
3. Which features are implemented and which are only placeholders.
4. Whether the application runs successfully.
5. Whether a complete video can currently be rendered.
6. What errors, missing dependencies, or configuration requirements remain.
7. The smallest practical next step toward producing a real video.

Do not modify files until the initial inspection and findings have been reported, unless a minimal diagnostic action is necessary to establish the application's status.

Then continue development incrementally, preserving existing work and testing each important change.

**Final guiding principle:** Shorts Studio must become a genuinely useful, locally runnable AI video production system that produces real videos reliably, with minimal unnecessary costs and minimal manual effort.
