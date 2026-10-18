"""
FastAPI application entry-point for Shorts Studio.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.schemas import ErrorResponse, HealthResponse

logger = logging.getLogger("shorts_studio")

_start_time: float = 0.0


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    global _start_time
    _start_time = time.time()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger.info("Shorts Studio %s starting up …", settings.APP_VERSION)

    # Initialise database (creates tables if needed)
    init_db()
    logger.info("Database initialised")

    # Ensure project / asset directories exist
    settings.ensure_directories()
    logger.info("Data directories verified")

    # Start the background pipeline orchestrator
    from app.services.pipeline_orchestrator import orchestrator
    orchestrator.start()
    logger.info("Pipeline orchestrator started ✓")

    logger.info("Startup complete ✓")
    yield
    logger.info("Shorts Studio shutting down …")
    orchestrator.stop()


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Shorts Studio API",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
        ).model_dump(),
    )


# ── Health check ─────────────────────────────────────────────────────────────

def _make_health_response():
    ffmpeg_bin = settings.detect_ffmpeg()
    ffmpeg_ok = Path(ffmpeg_bin).exists()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        uptime_seconds=round(time.time() - _start_time, 2) if _start_time else None,
        ffmpeg_available=ffmpeg_ok,
        ffmpeg=ffmpeg_ok,
        providers={
            "Local SAPI / TTS": {"configured": True},
            "Procedural Visuals": {"configured": True},
            "OpenAI": {"configured": bool(settings.OPENAI_API_KEY)},
            "ElevenLabs": {"configured": bool(settings.ELEVENLABS_API_KEY)},
            "Pexels": {"configured": bool(settings.PEXELS_API_KEY)},
        },
    )


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    return _make_health_response()


# ── Render output streaming endpoint ────────────────────────────────────────

@app.get("/api/v1/projects/{project_id}/assets/render-output/file", tags=["render"])
async def stream_render_output(project_id: str, path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        return JSONResponse(status_code=404, content={"detail": "Render output file not found"})
    return FileResponse(str(p), media_type="video/mp4", filename=p.name)


# ── API routers ──────────────────────────────────────────────────────────────

from app.routes.projects import router as projects_router  # noqa: E402
from app.routes.scripts import router as scripts_router  # noqa: E402
from app.routes.scenes import router as scenes_router  # noqa: E402
from app.routes.assets import router as assets_router  # noqa: E402
from app.routes.jobs import router as jobs_router  # noqa: E402
from app.routes.settings import router as settings_router  # noqa: E402
from app.routes.render import router as render_router  # noqa: E402
from app.routes.quality import router as quality_router  # noqa: E402
from app.routes.captions import router as captions_router  # noqa: E402
from app.routes.logs import router as logs_router  # noqa: E402

app.include_router(projects_router, prefix="/api/v1", tags=["projects"])
app.include_router(scripts_router, prefix="/api/v1", tags=["scripts"])
app.include_router(scenes_router, prefix="/api/v1", tags=["scenes"])
app.include_router(assets_router, prefix="/api/v1", tags=["assets"])
app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(render_router, prefix="/api/v1", tags=["render"])
app.include_router(quality_router, prefix="/api/v1", tags=["quality"])
app.include_router(captions_router, prefix="/api/v1", tags=["captions"])
app.include_router(logs_router, prefix="/api/v1", tags=["logs"])


# ── Static files / SPA fallback ─────────────────────────────────────────────

_frontend_dir = Path(r"d:\Antigravity.google\ShortsStudio\frontend")

if _frontend_dir.exists():
    css_dir = _frontend_dir / "css"
    js_dir = _frontend_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve index.html for all non-API web and SPA/hash routes."""
    # Check if a direct file in frontend exists
    target = _frontend_dir / full_path
    if full_path and target.exists() and target.is_file():
        return FileResponse(str(target))

    index_path = _frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        {"message": "Shorts Studio API is running. Frontend not found at /static."},
    )
