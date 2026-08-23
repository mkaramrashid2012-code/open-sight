"""OpenSight Private API - Enterprise-Grade Main Application Entry Point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.cameras import router as cameras_router
from app.api.search import router as search_router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.core.db import init_database, db_manager

# Configure enterprise-grade logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)
    logger.info(f"Environment: {'production' if not settings.debug else 'development'}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    logger.info(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    
    # Initialize storage directories
    for path in [settings.media_root, settings.clips_root, settings.thumbnails_root]:
        Path(path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directory ready: {path}")
    
    # Initialize database with connection pooling
    try:
        init_database()
        db_status = db_manager.health_check()
        logger.info(f"Database initialized: {db_status['status']}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    logger.info(f"YOLO Model: {settings.model_path} (device: {settings.model_device})")
    logger.info(f"Processing FPS target: {settings.processing_fps_target}")
    logger.info(f"Max concurrent cameras: {settings.max_concurrent_cameras}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpenSight Private API...")
    from app.workers import get_pipeline_manager
    manager = get_pipeline_manager()
    if manager:
        logger.info("Stopping all camera workers...")
        manager.stop_all()
        logger.info("All camera workers stopped")
    
    # Close database connections
    db_manager.close()
    logger.info("Database connections closed")
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise-grade local video analytics platform for CCTV/IP camera surveillance with privacy-first design",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# Configure CORS with allowed origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Processing-Time"],
)


# Mount static files for media access
media_path = Path(settings.media_root)
if media_path.exists():
    app.mount("/media", StaticFiles(directory=str(media_path)), name="media")
    logger.info(f"Media files served from: {media_path}")


# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cameras_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


# Global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        } if not settings.debug else {
            "error": "internal_error",
            "message": str(exc),
            "type": type(exc).__name__,
        },
    )


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Comprehensive health check endpoint."""
    from datetime import datetime, timezone
    
    db_health = db_manager.health_check()
    
    return {
        "status": "healthy" if db_health.get("healthy", False) else "degraded",
        "service": "opensight-api",
        "version": settings.app_version,
        "database": db_health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/status", tags=["Health"])
def system_status():
    """Get comprehensive system status including pipeline state."""
    from app.workers import get_pipeline_manager
    
    manager = get_pipeline_manager()
    active_cameras = []
    worker_stats = []
    
    if manager:
        for cam_id, worker in manager.workers.items():
            active_cameras.append(str(cam_id))
            worker_stats.append({
                "camera_id": str(cam_id),
                "running": worker._running,
                "frame_count": worker._frame_count,
            })
    
    db_health = db_manager.health_check()
    
    return {
        "status": "running",
        "version": settings.app_version,
        "active_camera_workers": len(active_cameras),
        "camera_ids": active_cameras,
        "worker_statistics": worker_stats,
        "database": db_health,
        "storage": {
            "media_root": str(settings.media_root),
            "clips_root": str(settings.clips_root),
            "thumbnails_root": str(settings.thumbnails_root),
            "retention_days": settings.default_retention_days,
        },
        "processing": {
            "fps_target": settings.processing_fps_target,
            "model": settings.model_path,
            "device": settings.model_device,
            "confidence_threshold": settings.confidence_threshold,
        },
    }


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Local video analytics platform for CCTV/IP camera surveillance",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/api/v1/health",
        "status": "/api/v1/status",
    }
