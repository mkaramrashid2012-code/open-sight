"""Search module with ReID support for BriefCam-like video synopsis."""
from app.search.reid import (
    ReIDFeatures,
    ReIDEmbedder,
    ReIDMatcher,
    get_embedder,
    get_matcher,
)

__all__ = [
    "ReIDFeatures",
    "ReIDEmbedder",
    "ReIDMatcher",
    "get_embedder",
    "get_matcher",
]
