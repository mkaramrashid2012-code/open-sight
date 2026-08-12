from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Detection

router = APIRouter(prefix="/search", tags=["search"])

class SearchRequest(BaseModel):
    camera_id: str | None = None
    object_class: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    min_confidence: float = 0.0
    limit: int = 100

@router.post("")
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    q = select(Detection).where(Detection.confidence >= payload.min_confidence).order_by(Detection.timestamp.desc()).limit(min(payload.limit, 500))
    if payload.camera_id: q = q.where(Detection.camera_id == payload.camera_id)
    if payload.object_class: q = q.where(Detection.object_class == payload.object_class)
    if payload.start: q = q.where(Detection.timestamp >= payload.start)
    if payload.end: q = q.where(Detection.timestamp <= payload.end)
    rows = db.scalars(q).all()
    return [{"id": str(x.id), "camera_id": str(x.camera_id), "timestamp": x.timestamp, "object_class": x.object_class, "confidence": x.confidence, "track_id": x.track_id, "bbox": x.bbox, "attributes": x.attributes} for x in rows]
