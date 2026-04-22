"""
FastAPI Application Entry Point
Agentic AI HR System
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import init_db
from app.db.seed import seed_database
from app.db.database import AsyncSessionLocal
from app.core.scheduler import start_scheduler, stop_scheduler


# ── Logging ───────────────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    level="DEBUG" if settings.DEBUG else "INFO",
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    enqueue=True,
)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.APP_NAME} [{settings.APP_ENV}]")

    # Initialize DB tables
    await init_db()

    # Seed demo data on first run
    async with AsyncSessionLocal() as db:
        await seed_database(db)
        await db.commit()

    # Start background scheduler
    start_scheduler()

    logger.info("✅ Application ready")
    yield

    # Shutdown
    stop_scheduler()
    logger.info("👋 Application shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-grade Agentic AI HR System",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )
