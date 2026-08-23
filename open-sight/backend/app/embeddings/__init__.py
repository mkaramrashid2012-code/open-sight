"""Embeddings package initialization."""
from app.embeddings.appearance import DeepAppearanceEngine, AppearanceEmbedding

# Backward compatibility alias
AppearanceEmbedder = DeepAppearanceEngine

__all__ = ["DeepAppearanceEngine", "AppearanceEmbedding", "AppearanceEmbedder"]
