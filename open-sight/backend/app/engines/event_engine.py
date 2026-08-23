"""
Event Engine
Converts raw tracks into semantic events (Intrusion, Loitering, etc.)
"""
import logging
from typing import List
from datetime import datetime

from app.services.tracker_service import TrackedObject, TrackState
from app.models.entities import Event, EventType
from app.core.config import settings

logger = logging.getLogger(__name__)


class EventEngine:
    def __init__(self):
        # Simple state for event generation
        self.active_events: dict = {}  # track_id -> Event
        
    async def process_tracks(self, tracks: List[TrackedObject], camera_id: int) -> List[Event]:
        """
        Analyze tracks and generate semantic events.
        Rules:
        - Person/Vehicle Detected: New track appears
        - Loitering: Track stays in same area > threshold time
        - Intrusion: Track enters a defined zone (future)
        """
        generated_events = []
        
        for track in tracks:
            if track.state not in [TrackState.ACTIVE, TrackState.TENTATIVE]:
                continue
                
            # 1. Check for new detections (Person/Vehicle Detected)
            if track.detection_count == 1:
                event = self._create_event(
                    camera_id=camera_id,
                    track_id=track.track_id,
                    event_type=EventType.OBJECT_DETECTED,
                    confidence=track.confidence,
                    metadata={"class": track.class_name}
                )
                generated_events.append(event)
                self.active_events[track.track_id] = event
                
            # 2. Check for Loitering (track age > threshold)
            elif track.detection_count > 10: # Simplified: based on frame count
                age_seconds = (datetime.utcnow() - track.first_seen).total_seconds()
                if age_seconds > settings.EVENT_LOITERING_THRESHOLD_SEC:
                    # Check if we already fired a loitering event for this track
                    if track.track_id not in self.active_events or \
                       self.active_events[track.track_id].event_type != EventType.LOITERING:
                       
                        event = self._create_event(
                            camera_id=camera_id,
                            track_id=track.track_id,
                            event_type=EventType.LOITERING,
                            confidence=track.quality_score,
                            metadata={
                                "duration_sec": age_seconds,
                                "class": track.class_name
                            }
                        )
                        generated_events.append(event)
                        self.active_events[track.track_id] = event

            # 3. Check for track end to close events
            if track.track_id in self.active_events:
                if track.state == TrackState.ENDED or track.state == TrackState.LOST:
                    # Close the event
                    closed_event = self.active_events.pop(track.track_id)
                    # In real impl, update DB with end_time
                    
        return generated_events

    def _create_event(
        self, 
        camera_id: int, 
        track_id: int, 
        event_type: EventType, 
        confidence: float,
        metadata: dict
    ) -> Event:
        now = datetime.utcnow()
        return Event(
            camera_id=camera_id,
            track_id=track_id,
            event_type=event_type,
            start_time=now,
            end_time=None,
            duration=0,
            confidence=confidence,
            thumbnail_path=None,
            clip_path=None,
            metadata=metadata,
            created_at=now
        )
