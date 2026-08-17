"""Camera management API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Camera
from app.workers import get_pipeline_manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rtsp_url: str
    enabled: bool = True


class CameraOut(CameraCreate):
    id: UUID
    model_config = {"from_attributes": True}


@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    """List all registered cameras."""
    return list(db.scalars(select(Camera).order_by(Camera.name)))


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    """Register a new camera and start processing if enabled."""
    if db.scalar(select(Camera).where(Camera.name == payload.name)):
        raise HTTPException(409, "Camera name already exists")
    
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    
    # Start processing pipeline for this camera if enabled
    if camera.enabled:
        manager = get_pipeline_manager()
        if manager:
            manager.start_camera(camera)
    
    return camera


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: UUID, db: Session = Depends(get_db)):
    """Delete a camera and stop its processing pipeline."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    
    # Stop processing pipeline for this camera
    manager = get_pipeline_manager()
    if manager:
        manager.stop_camera(camera_id)
    
    db.delete(camera)
    db.commit()


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: UUID, db: Session = Depends(get_db)):
    """Get details of a specific camera."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    return camera


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: UUID, payload: CameraCreate, db: Session = Depends(get_db)):
    """Update camera configuration and restart pipeline if needed."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    
    # Check for duplicate name
    existing = db.scalar(select(Camera).where(
        (Camera.name == payload.name) & (Camera.id != camera_id)
    ))
    if existing:
        raise HTTPException(409, "Camera name already exists")
    
    # Update fields
    camera.name = payload.name
    camera.rtsp_url = payload.rtsp_url
    
    was_enabled = camera.enabled
    camera.enabled = payload.enabled
    
    manager = get_pipeline_manager()
    
    # Handle state changes
    if payload.enabled and not was_enabled:
        # Start processing
        if manager:
            manager.start_camera(camera)
    elif not payload.enabled and was_enabled:
        # Stop processing
        if manager:
            manager.stop_camera(camera_id)
    elif payload.enabled and was_enabled:
        # Restart with new RTSP URL if changed
        if manager:
            manager.stop_camera(camera_id)
            manager.start_camera(camera)
    
    db.commit()
    db.refresh(camera)
    return camera


@router.post("/{camera_id}/start", status_code=200)
def start_camera_processing(camera_id: UUID, db: Session = Depends(get_db)):
    """Start video processing for a camera."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    
    if not camera.enabled:
        raise HTTPException(400, "Camera is disabled. Enable it first.")
    
    manager = get_pipeline_manager()
    if not manager:
        raise HTTPException(503, "Pipeline manager not initialized")
    
    manager.start_camera(camera)
    return {"status": "started", "camera_id": str(camera_id)}


@router.post("/{camera_id}/stop", status_code=200)
def stop_camera_processing(camera_id: UUID, db: Session = Depends(get_db)):
    """Stop video processing for a camera."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    
    manager = get_pipeline_manager()
    if not manager:
        raise HTTPException(503, "Pipeline manager not initialized")
    
    manager.stop_camera(camera_id)
    return {"status": "stopped", "camera_id": str(camera_id)}


@router.get("/{camera_id}/status")
def get_camera_status(camera_id: UUID, db: Session = Depends(get_db)):
    """Get processing status for a camera."""
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    
    manager = get_pipeline_manager()
    is_processing = manager and camera_id in manager.workers
    
    return {
        "camera_id": str(camera_id),
        "name": camera.name,
        "enabled": camera.enabled,
        "processing": is_processing,
        "rtsp_url": camera.rtsp_url,
    }
