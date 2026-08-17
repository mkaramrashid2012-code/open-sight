"""Event search API endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Detection, Camera

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    camera_id: Optional[str] = None
    object_class: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    min_confidence: float = 0.0
    track_id: Optional[int] = None
    limit: int = Field(default=100, le=500)


class DetectionResponse(BaseModel):
    id: str
    camera_id: str
    camera_name: Optional[str] = None
    timestamp: datetime
    object_class: str
    confidence: float
    track_id: Optional[int]
    bbox: list[float]
    attributes: dict
    thumbnail_url: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("", response_model=list[DetectionResponse])
def search_detections(payload: SearchRequest, db: Session = Depends(get_db)):
    """Search detections with filters."""
    q = select(Detection).where(
        Detection.confidence >= payload.min_confidence
    ).order_by(Detection.timestamp.desc()).limit(payload.limit)
    
    if payload.camera_id:
        try:
            camera_uuid = UUID(payload.camera_id)
            q = q.where(Detection.camera_id == camera_uuid)
        except ValueError:
            pass
    
    if payload.object_class:
        q = q.where(Detection.object_class.ilike(f"%{payload.object_class}%"))
    
    if payload.start:
        q = q.where(Detection.timestamp >= payload.start)
    
    if payload.end:
        q = q.where(Detection.timestamp <= payload.end)
    
    if payload.track_id is not None:
        q = q.where(Detection.track_id == payload.track_id)
    
    rows = db.scalars(q).all()
    
    # Build response with camera names and thumbnail URLs
    camera_cache = {}
    results = []
    for det in rows:
        camera_name = None
        if det.camera_id not in camera_cache:
            cam = db.get(Camera, det.camera_id)
            camera_cache[det.camera_id] = cam.name if cam else None
        camera_name = camera_cache[det.camera_id]
        
        thumbnail_url = None
        if "thumbnail" in det.attributes:
            thumbnail_url = f"/media/{det.attributes['thumbnail']}"
        
        results.append({
            "id": str(det.id),
            "camera_id": str(det.camera_id),
            "camera_name": camera_name,
            "timestamp": det.timestamp,
            "object_class": det.object_class,
            "confidence": det.confidence,
            "track_id": det.track_id,
            "bbox": det.bbox,
            "attributes": det.attributes,
            "thumbnail_url": thumbnail_url,
        })
    
    return results


@router.get("/tracks")
def search_tracks(
    camera_id: Optional[str] = None,
    object_class: Optional[str] = None,
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    db: Session = Depends(get_db),
):
    """Get unique tracks with summary information."""
    q = select(
        Detection.track_id,
        Detection.camera_id,
        Detection.object_class,
        func.min(Detection.timestamp).label("first_seen"),
        func.max(Detection.timestamp).label("last_seen"),
        func.count(Detection.id).label("detection_count"),
        func.avg(Detection.confidence).label("avg_confidence"),
    ).where(
        Detection.track_id.isnot(None),
        Detection.confidence >= min_confidence,
    ).group_by(
        Detection.track_id,
        Detection.camera_id,
        Detection.object_class,
    ).order_by(func.max(Detection.timestamp).desc())
    
    if camera_id:
        try:
            camera_uuid = UUID(camera_id)
            q = q.where(Detection.camera_id == camera_uuid)
        except ValueError:
            pass
    
    if object_class:
        q = q.where(Detection.object_class.ilike(f"%{object_class}%"))
    
    rows = db.execute(q).all()
    
    return [
        {
            "track_id": row.track_id,
            "camera_id": str(row.camera_id),
            "object_class": row.object_class,
            "first_seen": row.first_seen,
            "last_seen": row.last_seen,
            "detection_count": row.detection_count,
            "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0.0,
        }
        for row in rows
    ]


@router.get("/summary")
def get_summary(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Get detection summary statistics."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    
    # Total detections
    total = db.scalar(
        select(func.count(Detection.id)).where(Detection.timestamp >= cutoff)
    )
    
    # Detections by class
    by_class = db.execute(
        select(
            Detection.object_class,
            func.count(Detection.id).label("count")
        )
        .where(Detection.timestamp >= cutoff)
        .group_by(Detection.object_class)
        .order_by(func.count(Detection.id).desc())
    ).all()
    
    # Active cameras
    active_cameras = db.scalar(
        select(func.count(Camera.id)).where(Camera.enabled == True)
    )
    
    return {
        "period_days": days,
        "total_detections": total or 0,
        "by_class": [{"class": r.object_class, "count": r.count} for r in by_class],
        "active_cameras": active_cameras or 0,
    }
