"""
Real-time WebSocket Server for Live Camera Streaming and Event Notifications
Enterprise-grade bidirectional communication for dashboard updates
"""
import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass

try:
    from fastapi import WebSocket, WebSocketDisconnect
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocket = object
    WebSocketDisconnect = Exception

logger = logging.getLogger(__name__)


@dataclass
class WebSocketMessage:
    """Standardized WebSocket message structure"""
    type: str  # "camera_frame", "event", "status", "error"
    data: Dict[str, Any]
    timestamp: str = None
    camera_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id
        })


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    Supports broadcasting to specific cameras or all clients
    """
    
    def __init__(self):
        # Active connections: {websocket: set of camera_ids}
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        # Subscriptions by camera: {camera_id: set of websockets}
        self.camera_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Global subscribers (receive all events)
        self.global_subscribers: Set[WebSocket] = set()
        
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, camera_ids: Optional[list] = None):
        """Accept WebSocket connection and optionally subscribe to cameras"""
        await websocket.accept()
        self.active_connections[websocket] = set(camera_ids or [])
        
        # Add to camera subscriptions
        if camera_ids:
            for camera_id in camera_ids:
                if camera_id not in self.camera_subscriptions:
                    self.camera_subscriptions[camera_id] = set()
                self.camera_subscriptions[camera_id].add(websocket)
        else:
            # No specific cameras = global subscriber
            self.global_subscribers.add(websocket)
        
        logger.info(f"WebSocket connected. Cameras: {camera_ids or 'all'}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket not in self.active_connections:
            return
        
        # Remove from camera subscriptions
        camera_ids = self.active_connections[websocket]
        for camera_id in camera_ids:
            if camera_id in self.camera_subscriptions:
                self.camera_subscriptions[camera_id].discard(websocket)
                if not self.camera_subscriptions[camera_id]:
                    del self.camera_subscriptions[camera_id]
        
        # Remove from global subscribers
        self.global_subscribers.discard(websocket)
        
        # Remove from active connections
        del self.active_connections[websocket]
        
        logger.info(f"WebSocket disconnected. Was subscribed to: {camera_ids}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_camera(self, message: str, camera_id: str):
        """Broadcast message to all subscribers of a specific camera"""
        if camera_id not in self.camera_subscriptions:
            return
        
        disconnected = []
        for websocket in self.camera_subscriptions[camera_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to camera {camera_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_global(self, message: str):
        """Broadcast message to all global subscribers"""
        disconnected = []
        for websocket in self.global_subscribers:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast globally: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_event(self, event_data: Dict, camera_id: Optional[str] = None):
        """
        Broadcast event to relevant subscribers
        If camera_id provided, send to camera subscribers + global
        Otherwise, send to global only
        """
        message = WebSocketMessage(
            type="event",
            data=event_data,
            camera_id=camera_id
        ).to_json()
        
        if camera_id:
            # Send to camera-specific subscribers
            await self.broadcast_to_camera(message, camera_id)
            # Also send to global subscribers
            await self.broadcast_global(message)
        else:
            await self.broadcast_global(message)
    
    async def broadcast_frame(self, frame_data: bytes, camera_id: str, 
                             metadata: Optional[Dict] = None):
        """
        Broadcast video frame to camera subscribers
        Sends binary data for efficiency
        """
        # Prepare metadata
        msg_metadata = {
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "frame_size": len(frame_data)
        }
        if metadata:
            msg_metadata.update(metadata)
        
        # Send to camera subscribers
        if camera_id in self.camera_subscriptions:
            disconnected = []
            for websocket in self.camera_subscriptions[camera_id]:
                try:
                    # Send binary frame
                    await websocket.send_bytes(frame_data)
                    # Send metadata as text
                    await websocket.send_text(json.dumps({
                        "type": "frame_metadata",
                        "data": msg_metadata
                    }))
                except Exception as e:
                    logger.error(f"Failed to send frame to camera {camera_id}: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for ws in disconnected:
                self.disconnect(ws)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_camera_subscriber_count(self, camera_id: str) -> int:
        """Get number of subscribers for a specific camera"""
        return len(self.camera_subscriptions.get(camera_id, set()))
    
    def get_statistics(self) -> Dict:
        """Get connection manager statistics"""
        return {
            "total_connections": len(self.active_connections),
            "global_subscribers": len(self.global_subscribers),
            "camera_subscriptions": {
                cam_id: len(subs) 
                for cam_id, subs in self.camera_subscriptions.items()
            },
            "connections_by_camera": {
                cam_id: len(subs) 
                for cam_id, subs in self.camera_subscriptions.items()
            }
        }


# Singleton instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, camera_ids: Optional[str] = None):
    """
    FastAPI WebSocket endpoint handler
    Usage: @app.websocket("/ws")
    """
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket support not available")
        return
    
    # Parse camera IDs from query parameter
    cameras = None
    if camera_ids:
        cameras = [cid.strip() for cid in camera_ids.split(",") if cid.strip()]
    
    await manager.connect(websocket, cameras)
    
    try:
        while True:
            # Keep connection alive, handle ping/pong
            data = await websocket.receive_text()
            
            # Handle client messages (optional: commands, acknowledgments)
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "subscribe":
                    # Client wants to subscribe to additional cameras
                    new_cameras = message.get("camera_ids", [])
                    for cam_id in new_cameras:
                        if cam_id not in manager.camera_subscriptions:
                            manager.camera_subscriptions[cam_id] = set()
                        manager.camera_subscriptions[cam_id].add(websocket)
                        if websocket in manager.active_connections:
                            manager.active_connections[websocket].add(cam_id)
                    
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "data": {"camera_ids": list(manager.active_connections.get(websocket, set()))}
                    }))
                elif msg_type == "unsubscribe":
                    # Client wants to unsubscribe from cameras
                    remove_cameras = message.get("camera_ids", [])
                    for cam_id in remove_cameras:
                        if cam_id in manager.camera_subscriptions:
                            manager.camera_subscriptions[cam_id].discard(websocket)
                        if websocket in manager.active_connections:
                            manager.active_connections[websocket].discard(cam_id)
                    
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "data": {"camera_ids": list(manager.active_connections.get(websocket, set()))}
                    }))
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client: {data[:100]}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
