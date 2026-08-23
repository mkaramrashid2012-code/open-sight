"""Database session module for backward compatibility."""
from app.db import AsyncSessionLocal, async_engine as engine

__all__ = ["AsyncSessionLocal", "engine"]
