"""Search module with ReID support for BriefCam-like video synopsis."""
from app.search.reid import (
    ReIDFeatures,
    ReIDEmbedder,
    CrossCameraTracker,
    init_cross_camera_tracker,
    get_cross_camera_tracker,
)

__all__ = [
    "ReIDFeatures",
    "ReIDEmbedder",
    "CrossCameraTracker",
    "init_cross_camera_tracker",
    "get_cross_camera_tracker",
]
