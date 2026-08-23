"""Enterprise-grade configuration management for OpenSight Private."""
import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database
    database_url: str = Field(
        default="postgresql+psycopg://opensight:change-me@localhost:5432/opensight",
        description="PostgreSQL connection URL with pgvector support"
    )
    
    # Async Database (derived from database_url)
    @property
    def async_database_url(self) -> str:
        """Convert sync database URL to async one."""
        if self.database_url.startswith("postgresql+psycopg://"):
            return self.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url
    
    # Security
    secret_key: str = Field(
        default="",
        description="Secret key for JWT tokens and session encryption"
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:8501", "http://127.0.0.1:8501"],
        description="Allowed CORS origins"
    )
    allow_anonymous: bool = Field(
        default=True,
        description="Allow anonymous API access (disable in production)"
    )
    
    # Storage
    media_root: str = Field(
        default="./data/media",
        description="Root directory for media storage"
    )
    clips_root: str = Field(
        default="./data/clips",
        description="Root directory for video clips"
    )
    thumbnails_root: str = Field(
        default="./data/thumbnails",
        description="Root directory for thumbnails"
    )
    default_retention_days: int = Field(
        default=14,
        ge=1,
        le=365,
        description="Default retention period for media files in days"
    )
    max_clip_duration_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Maximum duration for saved video clips"
    )
    
    # ML Models
    model_path: str = Field(
        default="yolov8n.pt",
        description="Path to YOLO model or ultralytics model identifier"
    )
    yolo_model_path: str = Field(
        default="yolov8n.pt",
        description="Path to YOLO model or ultralytics model identifier"
    )
    use_gpu: bool = Field(
        default=False,
        description="Enable GPU acceleration for inference"
    )
    detection_confidence_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for detections"
    )
    detection_iou_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="IoU threshold for NMS"
    )
    detection_classes_filter: list[int] = Field(
        default=[],
        description="List of class IDs to filter (empty for all classes)"
    )
    confidence_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for detections"
    )
    iou_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="IoU threshold for NMS"
    )
    model_device: str = Field(
        default="cpu",
        description="Device for model inference (cpu, cuda, mps)"
    )
    
    # Video Processing
    processing_fps_target: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="Target frames per second for processing"
    )
    skip_frames: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Number of frames to skip between processing"
    )
    frame_buffer_size: int = Field(
        default=30,
        ge=10,
        le=100,
        description="Size of frame buffer for clip generation"
    )
    rtsp_timeout_seconds: int = Field(
        default=10,
        ge=5,
        le=60,
        description="RTSP connection timeout in seconds"
    )
    reconnect_delay_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Delay between reconnection attempts"
    )
    
    # Performance & Resource Management
    max_concurrent_cameras: int = Field(
        default=16,
        ge=1,
        le=64,
        description="Maximum number of concurrent camera streams"
    )
    worker_thread_pool_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=32,
        description="Size of worker thread pool (None for auto)"
    )
    db_pool_size: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Database connection pool size"
    )
    db_max_overflow: int = Field(
        default=20,
        ge=0,
        le=50,
        description="Database connection pool overflow"
    )
    
    # Logging & Monitoring
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        description="Log format string"
    )
    enable_metrics: bool = Field(
        default=False,
        description="Enable Prometheus-style metrics endpoint"
    )
    enable_audit_logging: bool = Field(
        default=True,
        description="Enable audit trail for sensitive operations"
    )
    
    # Retention Policies
    retention_check_interval_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="How often to run retention cleanup (in hours)"
    )
    retention_event_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to retain event records"
    )
    retention_media_days: int = Field(
        default=14,
        ge=1,
        le=365,
        description="Days to retain media files (thumbnails, clips)"
    )
    
    # Camera Settings
    camera_max_reconnect_attempts: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum reconnection attempts before giving up"
    )
    
    # Tracking Settings
    track_max_misses: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Maximum consecutive misses before marking track as lost"
    )
    track_iou_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="IoU threshold for track-detection matching"
    )
    track_trajectory_max_length: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum number of points to store in track trajectory"
    )
    track_max_age: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Maximum age of track in seconds before cleanup"
    )
    
    # Application
    app_name: str = "OpenSight Private"
    app_version: str = "1.0.0"
    debug: bool = Field(
        default=False,
        description="Enable debug mode (disable in production)"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port to bind the API server"
    )
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is set in production."""
        if not v and os.getenv('ENVIRONMENT', 'development') == 'production':
            raise ValueError("SECRET_KEY must be set in production environment")
        return v or "dev-secret-key-change-in-production"
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith('postgresql'):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
