from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Camera

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
    return list(db.scalars(select(Camera).order_by(Camera.name)))

@router.post("", response_model=CameraOut, status_code=201)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Camera).where(Camera.name == payload.name)):
        raise HTTPException(409, "Camera name already exists")
    camera = Camera(**payload.model_dump())
    db.add(camera); db.commit(); db.refresh(camera)
    return camera

@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: UUID, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera: raise HTTPException(404, "Camera not found")
    db.delete(camera); db.commit()
