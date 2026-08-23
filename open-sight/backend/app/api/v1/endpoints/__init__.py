"""API v1 endpoints package initialization."""
from app.api.cameras import router as cameras_router
from app.api.search import router as search_router

# Create simplified endpoint modules for backward compatibility
class ModuleProxy:
    def __init__(self, router, name):
        self.router = router
        self.__name__ = name

cameras = ModuleProxy(cameras_router, "cameras")
search = ModuleProxy(search_router, "search")

# Health and events endpoints will be created
import fastapi
from typing import Dict, Any

# Health endpoint
health_router = fastapi.APIRouter()

@health_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "opensight"}

events_router = fastapi.APIRouter()

@events_router.get("/")
async def list_events():
    return {"events": []}

health = ModuleProxy(health_router, "health")
events = ModuleProxy(events_router, "events")

__all__ = ["cameras", "search", "health", "events"]
