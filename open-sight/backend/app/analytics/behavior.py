"""
Advanced Behavioral Analytics Engine
Enterprise-grade event detection: intrusion, loitering, line-crossing, crowd detection, object abandonment
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    INTRUSION = "intrusion"
    LOITERING = "loitering"
    LINE_CROSSING = "line_crossing"
    CROWD_FORMATION = "crowd_formation"
    OBJECT_ABANDONMENT = "object_abandonment"
    WRONG_DIRECTION = "wrong_direction"
    SPEEDING = "speeding"
    FALL_DETECTION = "fall_detection"


@dataclass
class ZoneConfig:
    """Configuration for detection zones"""
    zone_id: str
    zone_name: str
    polygon: List[Tuple[int, int]]  # [(x1,y1), (x2,y2), ...]
    event_types: List[EventType]
    enabled: bool = True
    sensitivity: float = 0.7  # 0.0-1.0
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside polygon using ray casting algorithm"""
        n = len(self.polygon)
        inside = False
        p1x, p1y = self.polygon[0]
        for i in range(n + 1):
            p2x, p2y = self.polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside


@dataclass
class LineConfig:
    """Configuration for virtual lines"""
    line_id: str
    line_name: str
    start: Tuple[int, int]
    end: Tuple[int, int]
    direction: Optional[str] = None  # "A_to_B", "B_to_A", or None for both
    enabled: bool = True


@dataclass
class DetectedEvent:
    """Represents a detected behavioral event"""
    event_id: str
    event_type: EventType
    camera_id: str
    timestamp: datetime
    track_ids: List[int]
    confidence: float
    zone_id: Optional[str] = None
    line_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    snapshot_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "track_ids": self.track_ids,
            "confidence": self.confidence,
            "zone_id": self.zone_id,
            "line_id": self.line_id,
            "metadata": self.metadata,
            "snapshot_path": self.snapshot_path
        }


class BehavioralAnalyticsEngine:
    """
    Enterprise behavioral analytics engine comparable to BriefCam's situational awareness
    Detects complex events from tracking data
    """
    
    def __init__(self):
        self.zones: Dict[str, ZoneConfig] = {}
        self.lines: Dict[str, LineConfig] = {}
        
        # Track state for temporal analysis
        self.track_history: Dict[int, List[Tuple[datetime, int, int, float]]] = {}  # track_id -> [(time, x, y, confidence)]
        self.track_entry_time: Dict[int, Dict[str, datetime]] = {}  # track_id -> {zone_id: entry_time}
        self.track_crossings: Dict[int, Dict[str, int]] = {}  # track_id -> {line_id: crossing_count}
        self.object_presence: Dict[int, Dict[str, datetime]] = {}  # track_id -> {location_key: first_seen}
        
        # Configuration thresholds
        self.loitering_threshold = timedelta(seconds=30)
        self.crowd_density_threshold = 5  # objects per zone
        self.abandonment_threshold = timedelta(seconds=60)
        self.speed_thresholds = {"pedestrian": 2.5, "vehicle": 15.0}  # m/s (approximate)
        
        logger.info("Behavioral Analytics Engine initialized")
    
    def add_zone(self, config: ZoneConfig):
        """Add or update a detection zone"""
        self.zones[config.zone_id] = config
        logger.info(f"Added detection zone: {config.zone_name} ({config.zone_id})")
    
    def remove_zone(self, zone_id: str):
        """Remove a detection zone"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            logger.info(f"Removed detection zone: {zone_id}")
    
    def add_line(self, config: LineConfig):
        """Add or update a virtual line"""
        self.lines[config.line_id] = config
        logger.info(f"Added virtual line: {config.line_name} ({config.line_id})")
    
    def remove_line(self, line_id: str):
        """Remove a virtual line"""
        if line_id in self.lines:
            del self.lines[line_id]
            logger.info(f"Removed virtual line: {line_id}")
    
    def process_track_update(self, track_id: int, bbox: Tuple[int, int, int, int], 
                            confidence: float, camera_id: str, timestamp: datetime,
                            object_class: str = "person") -> List[DetectedEvent]:
        """
        Process a track update and detect behavioral events
        Returns list of detected events
        """
        events = []
        x_center = int((bbox[0] + bbox[2]) / 2)
        y_center = int((bbox[1] + bbox[3]) / 2)
        
        # Update track history
        if track_id not in self.track_history:
            self.track_history[track_id] = []
        self.track_history[track_id].append((timestamp, x_center, y_center, confidence))
        
        # Keep only last 60 seconds of history
        cutoff = timestamp - timedelta(seconds=60)
        self.track_history[track_id] = [
            h for h in self.track_history[track_id] if h[0] >= cutoff
        ]
        
        # Check zone-based events
        events.extend(self._check_zone_events(track_id, x_center, y_center, camera_id, timestamp, object_class))
        
        # Check line crossing events
        events.extend(self._check_line_crossing(track_id, x_center, y_center, camera_id, timestamp))
        
        # Check speed events
        events.extend(self._check_speed(track_id, camera_id, timestamp, object_class))
        
        # Check fall detection (simplified: aspect ratio change)
        events.extend(self._check_fall_detection(track_id, bbox, camera_id, timestamp))
        
        return events
    
    def _check_zone_events(self, track_id: int, x: int, y: int, camera_id: str, 
                          timestamp: datetime, object_class: str) -> List[DetectedEvent]:
        """Check for zone-based events (intrusion, loitering, crowd)"""
        events = []
        
        for zone_id, zone in self.zones.items():
            if not zone.enabled:
                continue
            
            if zone.contains_point(x, y):
                # Intrusion detection
                if EventType.INTRUSION in zone.event_types:
                    if track_id not in self.track_entry_time:
                        self.track_entry_time[track_id] = {}
                    
                    if zone_id not in self.track_entry_time[track_id]:
                        # First entry into zone
                        self.track_entry_time[track_id][zone_id] = timestamp
                        event = DetectedEvent(
                            event_id=f"intrusion_{camera_id}_{track_id}_{int(timestamp.timestamp())}",
                            event_type=EventType.INTRUSION,
                            camera_id=camera_id,
                            timestamp=timestamp,
                            track_ids=[track_id],
                            confidence=0.9,
                            zone_id=zone_id,
                            metadata={"zone_name": zone.zone_name, "object_class": object_class}
                        )
                        events.append(event)
                        logger.warning(f"Intrusion detected in zone {zone.zone_name}")
                
                # Loitering detection
                if EventType.LOITERING in zone.event_types:
                    if track_id in self.track_entry_time and zone_id in self.track_entry_time[track_id]:
                        entry_time = self.track_entry_time[track_id][zone_id]
                        duration = timestamp - entry_time
                        
                        if duration >= self.loitering_threshold:
                            # Only trigger once per threshold period
                            if duration < self.loitering_threshold + timedelta(seconds=5):
                                event = DetectedEvent(
                                    event_id=f"loitering_{camera_id}_{track_id}_{int(timestamp.timestamp())}",
                                    event_type=EventType.LOITERING,
                                    camera_id=camera_id,
                                    timestamp=timestamp,
                                    track_ids=[track_id],
                                    confidence=min(0.5 + (duration.total_seconds() / 120), 0.95),
                                    zone_id=zone_id,
                                    metadata={
                                        "zone_name": zone.zone_name,
                                        "duration_seconds": duration.total_seconds(),
                                        "object_class": object_class
                                    }
                                )
                                events.append(event)
                                logger.warning(f"Loitering detected in zone {zone.zone_name}: {duration.total_seconds():.1f}s")
        
        # Crowd detection (count objects in each zone)
        for zone_id, zone in self.zones.items():
            if not zone.enabled or EventType.CROWD_FORMATION not in zone.event_types:
                continue
            
            objects_in_zone = 0
            track_ids_in_zone = []
            for tid, history in self.track_history.items():
                if not history:
                    continue
                _, hx, hy, _ = history[-1]
                if zone.contains_point(hx, hy):
                    objects_in_zone += 1
                    track_ids_in_zone.append(tid)
            
            if objects_in_zone >= self.crowd_density_threshold:
                event = DetectedEvent(
                    event_id=f"crowd_{camera_id}_{zone_id}_{int(timestamp.timestamp())}",
                    event_type=EventType.CROWD_FORMATION,
                    camera_id=camera_id,
                    timestamp=timestamp,
                    track_ids=track_ids_in_zone,
                    confidence=min(0.6 + (objects_in_zone / 20), 0.95),
                    zone_id=zone_id,
                    metadata={
                        "zone_name": zone.zone_name,
                        "object_count": objects_in_zone,
                        "threshold": self.crowd_density_threshold
                    }
                )
                events.append(event)
                logger.warning(f"Crowd formation detected in zone {zone.zone_name}: {objects_in_zone} objects")
        
        return events
    
    def _check_line_crossing(self, track_id: int, x: int, y: int, camera_id: str,
                            timestamp: datetime) -> List[DetectedEvent]:
        """Check for line crossing events"""
        events = []
        
        if track_id not in self.track_crossings:
            self.track_crossings[track_id] = {}
        
        for line_id, line in self.lines.items():
            if not line.enabled:
                continue
            
            # Check if track crossed the line
            crossed = self._detect_line_crossing(track_id, line, x, y)
            
            if crossed:
                direction = self._get_crossing_direction(line, x, y)
                
                # Check direction constraint
                if line.direction and direction != line.direction:
                    continue
                
                self.track_crossings[track_id][line_id] = self.track_crossings[track_id].get(line_id, 0) + 1
                
                event = DetectedEvent(
                    event_id=f"line_cross_{camera_id}_{track_id}_{int(timestamp.timestamp())}",
                    event_type=EventType.LINE_CROSSING,
                    camera_id=camera_id,
                    timestamp=timestamp,
                    track_ids=[track_id],
                    confidence=0.85,
                    line_id=line_id,
                    metadata={
                        "line_name": line.line_name,
                        "direction": direction,
                        "crossing_count": self.track_crossings[track_id][line_id]
                    }
                )
                events.append(event)
                logger.info(f"Line crossing detected: {line.line_name} by track {track_id}")
        
        return events
    
    def _detect_line_crossing(self, track_id: int, line: LineConfig, x: int, y: int) -> bool:
        """Detect if track has crossed the line"""
        if track_id not in self.track_history or len(self.track_history[track_id]) < 2:
            return False
        
        # Get previous position
        _, prev_x, prev_y, _ = self.track_history[track_id][-2]
        curr_x, curr_y = x, y
        
        # Line equation: ax + by + c = 0
        x1, y1 = line.start
        x2, y2 = line.end
        
        a = y1 - y2
        b = x2 - x1
        c = x1 * y2 - x2 * y1
        
        # Check if points are on different sides of the line
        prev_side = a * prev_x + b * prev_y + c
        curr_side = a * curr_x + b * curr_y + c
        
        return prev_side * curr_side < 0
    
    def _get_crossing_direction(self, line: LineConfig, x: int, y: int) -> str:
        """Determine crossing direction"""
        x1, y1 = line.start
        x2, y2 = line.end
        
        # Vector from line start to end
        line_vec = (x2 - x1, y2 - y1)
        # Vector from line start to point
        point_vec = (x - x1, y - y1)
        
        # Cross product to determine side
        cross = line_vec[0] * point_vec[1] - line_vec[1] * point_vec[0]
        
        return "A_to_B" if cross > 0 else "B_to_A"
    
    def _check_speed(self, track_id: int, camera_id: str, timestamp: datetime, 
                    object_class: str) -> List[DetectedEvent]:
        """Check for speeding events"""
        events = []
        
        if track_id not in self.track_history or len(self.track_history[track_id]) < 2:
            return events
        
        # Calculate speed from last two positions
        t1, x1, y1, _ = self.track_history[track_id][-2]
        t2, x2, y2, _ = self.track_history[track_id][-1]
        
        time_diff = (t2 - t1).total_seconds()
        if time_diff <= 0:
            return events
        
        # Pixel distance (simplified, assumes calibrated camera)
        pixel_distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        
        # Approximate conversion to meters (would need camera calibration in production)
        meters_per_pixel = 0.05  # 5cm per pixel (example)
        distance_meters = pixel_distance * meters_per_pixel
        speed_ms = distance_meters / time_diff
        
        threshold = self.speed_thresholds.get(object_class, 5.0)
        
        if speed_ms > threshold:
            event = DetectedEvent(
                event_id=f"speeding_{camera_id}_{track_id}_{int(timestamp.timestamp())}",
                event_type=EventType.SPEEDING,
                camera_id=camera_id,
                timestamp=timestamp,
                track_ids=[track_id],
                confidence=min(0.7 + (speed_ms / (threshold * 2)), 0.95),
                metadata={
                    "speed_ms": speed_ms,
                    "threshold_ms": threshold,
                    "object_class": object_class,
                    "speed_kmh": speed_ms * 3.6
                }
            )
            events.append(event)
            logger.warning(f"Speeding detected: {speed_ms:.2f} m/s (threshold: {threshold} m/s)")
        
        return events
    
    def _check_fall_detection(self, track_id: int, bbox: Tuple[int, int, int, int],
                             camera_id: str, timestamp: datetime) -> List[DetectedEvent]:
        """Simplified fall detection based on aspect ratio"""
        events = []
        
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        if height == 0:
            return events
        
        aspect_ratio = width / height
        
        # Person standing: aspect_ratio ~ 0.3-0.5
        # Person fallen: aspect_ratio > 1.0 (wider than tall)
        if aspect_ratio > 1.2:
            event = DetectedEvent(
                event_id=f"fall_{camera_id}_{track_id}_{int(timestamp.timestamp())}",
                event_type=EventType.FALL_DETECTION,
                camera_id=camera_id,
                timestamp=timestamp,
                track_ids=[track_id],
                confidence=min(0.6 + (aspect_ratio - 1.2) * 0.3, 0.9),
                metadata={
                    "aspect_ratio": aspect_ratio,
                    "bbox_width": width,
                    "bbox_height": height
                }
            )
            events.append(event)
            logger.warning(f"Possible fall detected for track {track_id}")
        
        return events
    
    def cleanup_old_tracks(self, max_age_seconds: int = 120):
        """Clean up old track history to prevent memory leaks"""
        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)
        
        # Clean track history
        expired_tracks = [
            tid for tid, history in self.track_history.items()
            if history and history[-1][0] < cutoff
        ]
        
        for tid in expired_tracks:
            self.track_history.pop(tid, None)
            self.track_entry_time.pop(tid, None)
            self.track_crossings.pop(tid, None)
            self.object_presence.pop(tid, None)
        
        if expired_tracks:
            logger.debug(f"Cleaned up {len(expired_tracks)} expired tracks")
