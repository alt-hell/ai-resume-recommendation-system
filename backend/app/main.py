"""
main.py
-------
FastAPI application entry point.

Registers:
  - All API routers (upload, extract, recommend, trends, job-links)
  - Startup / shutdown lifecycle
  - CORS middleware
  - Global exception handler
  - Health check endpoint
"""

import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import career_advisor, extract, job_links, recommend, resume_coach, trends, upload
from app.config import settings
from app.database.memory import close_db, connect_db, ping_db
from app.services.skill_extractor import preload_models

# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Silence noisy third-party loggers ─────────────────────────────────────
# pdfminer emits thousands of per-byte token DEBUG lines that block the
# event loop for minutes on complex PDFs. Force them to WARNING.
for _noisy in ("pdfminer", "pdfminer.psparser", "pdfminer.pdfinterp",
               "pdfminer.cmapdb", "pdfminer.pdfdocument", "pdfminer.pdfpage",
               "pdfminer.pdfparser", "pdfminer.converter", "pdfplumber"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan: startup + shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle.
    """
    logger.info("🚀 Starting %s v%s …", settings.APP_NAME, settings.VERSION)

    # ── Startup ────────────────────────────────────────────────────────────
    try:
        await connect_db()
    except Exception as exc:
        logger.error("⚠️  Startup failed: %s", exc)
        logger.warning("Running WITHOUT database. Persistence endpoints will fail.")

    # Pre-load heavy models (SpaCy + keyword registry) in the background so it
    # doesn't block startup but is ready before or during the first request.
    asyncio.create_task(asyncio.to_thread(preload_models))

    # Pre-load ML artifacts (XGBoost model, vectorizer, label encoder) so the
    # first upload doesn't pay the disk-loading penalty (~100ms).
    async def _preload_ml():
        try:
            from app.services.recommendation_engine import _load_artifacts
            await asyncio.to_thread(_load_artifacts)
            logger.info("ML artifacts pre-loaded successfully.")
        except Exception as exc:
            logger.warning("ML artifact preload skipped: %s", exc)
    asyncio.create_task(_preload_ml())

    yield  # ← Application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down …")
    await close_db()
    logger.info("✅ Shutdown complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "An end-to-end AI system that parses resumes, extracts and normalizes skills, "
        "predicts the best-matching job role using XGBoost, computes skill gaps, "
        "generates learning paths, and finds matching job listings.\n\n"
        "**Quick-start flow:**\n"
        "1. `POST /upload` — upload PDF/DOCX resume → get `resume_id`\n"
        "2. `GET /recommend/{resume_id}` — role prediction + skill gap\n"
        "3. `GET /job-links/{resume_id}` — top 5 matching job listings\n"
        "4. `GET /trends` — in-demand skills across the job market\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    """Log every request with method, path, status code, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Global exception handler
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — return a clean JSON error."""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred.",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns application status and database connectivity.",
)
async def health_check():
    db_ok = await ping_db()
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": "connected" if db_ok else "disconnected",
        "app": settings.APP_NAME,
    }


@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Register routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(recommend.router)
app.include_router(trends.router)
app.include_router(job_links.router)
app.include_router(resume_coach.router)
app.include_router(career_advisor.router)


logger.info(
    "Registered routes: %s",
    [route.path for route in app.routes if hasattr(route, "path")],
)
