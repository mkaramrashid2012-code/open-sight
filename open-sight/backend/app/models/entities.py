from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4
from sqlalchemy import DateTime, Float, Integer, String, Text, func, Enum as SQLEnum, Boolean, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
import enum
from app.core.db import Base


class TrackState(str, enum.Enum):
    """Track lifecycle states."""
    NEW = "new"
    TENTATIVE = "tentative"
    ACTIVE = "active"
    LOST = "lost"
    RECOVERED = "recovered"
    ENDED = "ended"


class EventType(str, enum.Enum):
    """Event types for video analytics."""
    PERSON_DETECTED = "person_detected"
    VEHICLE_DETECTED = "vehicle_detected"
    INTRUSION = "intrusion"
    LOITERING = "loitering"
    LINE_CROSSING = "line_crossing"
    CROWD = "crowd"
    OBJECT_ABANDONED = "object_abandoned"
    WRONG_DIRECTION = "wrong_direction"
    CAMERA_OFFLINE = "camera_offline"
    CAMERA_REONLINE = "camera_reonline"


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    rtsp_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(32), default="offline", index=True)  # offline, connecting, online, degraded, reconnecting, error, stopped
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fps_current: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frames_dropped: Mapped[int] = mapped_column(Integer, default=0)
    reconnect_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    detections: Mapped[list["Detection"]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    tracks: Mapped[list["Track"]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="camera", cascade="all, delete-orphan")


class Detection(Base):
    __tablename__ = "detections"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    object_class: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[list[float]] = mapped_column(JSONB)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(512), nullable=True)
    
    # Relationships
    camera: Mapped[Camera] = relationship(back_populates="detections")


class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_uuid: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, default=uuid4, index=True)
    camera_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)  # ByteTrack ID
    state: Mapped[str] = mapped_column(SQLEnum(TrackState), default=TrackState.NEW, index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    detection_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_bbox: Mapped[Optional[list[float]]] = mapped_column(JSONB, nullable=True)
    trajectory: Mapped[Optional[list[dict]]] = mapped_column(JSONB, default=list)  # List of {timestamp, center_x, center_y}
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    appearance_embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(512), nullable=True)
    
    # Relationships
    camera: Mapped[Camera] = relationship(back_populates="tracks")
    events: Mapped[list["Event"]] = relationship(back_populates="track", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tracks_camera_firstseen', 'camera_id', 'first_seen'),
        Index('ix_tracks_state_lastseen', 'state', 'last_seen'),
    )


class Event(Base):
    __tablename__ = "events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(SQLEnum(EventType), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clip_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    camera: Mapped[Camera] = relationship(back_populates="events")
    track: Mapped[Optional[Track]] = relationship(back_populates="events")
    
    __table_args__ = (
        Index('ix_events_type_starttime', 'event_type', 'start_time'),
        Index('ix_events_camera_createtime', 'camera_id', 'created_at'),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Role(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    SECURITY_MANAGER = "security_manager"
    OPERATOR = "operator"
    INVESTIGATOR = "investigator"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class UserRole(Base):
    """Many-to-many relationship between users and roles."""
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(SQLEnum(Role), primary_key=True)


class Permission(str, enum.Enum):
    """Permissions for RBAC."""
    CAMERA_READ = "camera.read"
    CAMERA_MANAGE = "camera.manage"
    EVENT_READ = "event.read"
    EVENT_EXPORT = "event.export"
    EVIDENCE_READ = "evidence.read"
    EVIDENCE_EXPORT = "evidence.export"
    USER_MANAGE = "user.manage"
    AUDIT_READ = "audit.read"
    SYSTEM_MANAGE = "system.manage"


class RolePermission(Base):
    """Many-to-many relationship between roles and permissions."""
    __tablename__ = "role_permissions"
    role: Mapped[str] = mapped_column(SQLEnum(Role), primary_key=True)
    permission: Mapped[str] = mapped_column(SQLEnum(Permission), primary_key=True)


class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    result: Mapped[str] = mapped_column(String(32))  # success, failure
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    user: Mapped[Optional[User]] = relationship(back_populates="audit_logs")
    
    __table_args__ = (
        Index('ix_audit_logs_timestamp_action', 'timestamp', 'action'),
    )


class EvidenceHold(Base):
    """Legal hold to prevent evidence deletion."""
    __tablename__ = "evidence_holds"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_ids: Mapped[list[UUID]] = mapped_column(JSONB, default=list)  # Events under hold
    
    __table_args__ = (
        Index('ix_evidence_holds_active', 'is_active', 'expires_at'),
    )
