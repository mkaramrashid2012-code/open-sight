"""
Advanced Analytics Engine for OpenSight Private
Provides heatmaps, intrusion detection, loitering alerts, and line crossing.
Enterprise-grade event detection comparable to BriefCam analytics.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ZoneConfig:
    """Configuration for a detection zone"""
    id: str
    name: str
    polygon: List[Tuple[int, int]]  # List of (x, y) points
    zone_type: str  # 'intrusion', 'loitering', 'exclusion'
    sensitivity: float = 0.7  # 0.0-1.0
    min_duration: float = 5.0  # seconds for loitering
    enabled: bool = True


@dataclass
class LineConfig:
    """Configuration for a virtual line"""
    id: str
    name: str
    start: Tuple[int, int]
    end: Tuple[int, int]
    direction: str = 'both'  # 'both', 'forward', 'backward'
    enabled: bool = True


@dataclass
class AnalyticsEvent:
    """Represents a detected analytics event"""
    event_id: str
    event_type: str  # 'intrusion', 'loitering', 'line_crossing', 'crowd'
    camera_id: str
    timestamp: datetime
    track_id: Optional[int]
    zone_id: Optional[str]
    line_id: Optional[str]
    confidence: float
    metadata: Dict = field(default_factory=dict)
    snapshot_path: Optional[str] = None


class AdvancedAnalytics:
    """
    Enterprise-grade analytics engine providing:
    - Intrusion detection (zone-based)
    - Loitering detection (time-based)
    - Line crossing counter
    - Crowd density estimation
    - Heatmap generation
    """
    
    def __init__(self):
        self.zones: Dict[str, ZoneConfig] = {}
        self.lines: Dict[str, LineConfig] = {}
        
        # Track state for analytics
        self.track_zones: Dict[int, Dict[str, datetime]] = defaultdict(dict)  # track_id -> {zone_id: enter_time}
        self.track_line_crossings: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.zone_entry_counts: Dict[str, int] = defaultdict(int)
        
        # Heatmap data
        self.heatmap_data: Dict[str, np.ndarray] = {}  # camera_id -> heatmap array
        self.heatmap_resolution = (640, 480)  # Reduced resolution for performance
        
        # Crowd detection thresholds
        self.crowd_density_threshold = 0.3  # objects per pixel ratio
        self.min_crowd_size = 5
        
        logger.info("Advanced Analytics Engine initialized")
    
    def add_zone(self, config: ZoneConfig):
        """Add or update a detection zone"""
        self.zones[config.id] = config
        logger.info(f"Added zone: {config.name} ({config.zone_type})")
        
        # Initialize heatmap if needed
        if config.zone_type == 'intrusion':
            # Will be populated when frames arrive
            pass
    
    def add_line(self, config: LineConfig):
        """Add or update a virtual line"""
        self.lines[config.id] = config
        logger.info(f"Added line: {config.name}")
    
    def remove_zone(self, zone_id: str):
        """Remove a detection zone"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            logger.info(f"Removed zone: {zone_id}")
    
    def remove_line(self, line_id: str):
        """Remove a virtual line"""
        if line_id in self.lines:
            del self.lines[line_id]
            logger.info(f"Removed line: {line_id}")
    
    def _point_in_polygon(self, point: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm"""
        x, y = point
        inside = False
        
        n = len(polygon)
        p1x, p1y = polygon[0]
        
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _calculate_distance_to_line(self, point: Tuple[int, int], 
                                     line_start: Tuple[int, int], 
                                     line_end: Tuple[int, int]) -> float:
        """Calculate perpendicular distance from point to line"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Line length squared
        l2 = (x1 - x2)**2 + (y1 - y2)**2
        
        if l2 == 0:
            return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # Project point onto line
        t = max(0, min(1, ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / l2))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        
        return np.sqrt((x0 - proj_x)**2 + (y0 - proj_y)**2)
    
    def process_tracks(self, camera_id: str, tracks: List[Dict], 
                       frame_timestamp: datetime) -> List[AnalyticsEvent]:
        """
        Process tracked objects and generate analytics events
        
        Args:
            camera_id: Camera identifier
            tracks: List of track dictionaries with 'id', 'bbox', 'center' keys
            frame_timestamp: Timestamp of the current frame
            
        Returns:
            List of detected analytics events
        """
        events = []
        
        for track in tracks:
            track_id = track.get('id')
            bbox = track.get('bbox', [0, 0, 0, 0])
            center = track.get('center', (0, 0))
            obj_class = track.get('class', 'person')
            
            # Update heatmap
            self._update_heatmap(camera_id, center)
            
            # Check zone interactions
            zone_events = self._check_zones(camera_id, track_id, center, 
                                           frame_timestamp, obj_class)
            events.extend(zone_events)
            
            # Check line crossings
            line_events = self._check_lines(camera_id, track_id, center, 
                                           frame_timestamp, obj_class)
            events.extend(line_events)
        
        # Check for crowd conditions
        crowd_events = self._check_crowd(camera_id, tracks, frame_timestamp)
        events.extend(crowd_events)
        
        return events
    
    def _check_zones(self, camera_id: str, track_id: int, center: Tuple[int, int],
                     timestamp: datetime, obj_class: str) -> List[AnalyticsEvent]:
        """Check for zone-based events (intrusion, loitering)"""
        events = []
        
        for zone_id, zone in self.zones.items():
            if not zone.enabled or zone.zone_type not in ['intrusion', 'loitering', 'exclusion']:
                continue
            
            is_inside = self._point_in_polygon(center, zone.polygon)
            
            if is_inside:
                # Track entry time
                if zone_id not in self.track_zones[track_id]:
                    self.track_zones[track_id][zone_id] = timestamp
                    self.zone_entry_counts[zone_id] += 1
                    
                    # Immediate intrusion event
                    if zone.zone_type == 'intrusion':
                        event = AnalyticsEvent(
                            event_id=f"INTR_{camera_id}_{zone_id}_{track_id}_{int(timestamp.timestamp())}",
                            event_type='intrusion',
                            camera_id=camera_id,
                            timestamp=timestamp,
                            track_id=track_id,
                            zone_id=zone_id,
                            confidence=zone.sensitivity,
                            metadata={
                                'object_class': obj_class,
                                'zone_name': zone.name,
                                'entry_time': timestamp.isoformat()
                            }
                        )
                        events.append(event)
                        logger.warning(f"Intrusion detected: {zone.name} by track {track_id}")
                
                # Check loitering
                elif zone.zone_type == 'loitering':
                    enter_time = self.track_zones[track_id][zone_id]
                    duration = (timestamp - enter_time).total_seconds()
                    
                    if duration >= zone.min_duration:
                        event = AnalyticsEvent(
                            event_id=f"LOIT_{camera_id}_{zone_id}_{track_id}_{int(timestamp.timestamp())}",
                            event_type='loitering',
                            camera_id=camera_id,
                            timestamp=timestamp,
                            track_id=track_id,
                            zone_id=zone_id,
                            confidence=min(1.0, duration / (zone.min_duration * 2)),
                            metadata={
                                'object_class': obj_class,
                                'zone_name': zone.name,
                                'duration_seconds': duration,
                                'enter_time': enter_time.isoformat()
                            }
                        )
                        events.append(event)
                        logger.warning(f"Loitering detected: {zone.name} by track {track_id} ({duration:.1f}s)")
            else:
                # Object left the zone
                if zone_id in self.track_zones[track_id]:
                    enter_time = self.track_zones[track_id][zone_id]
                    duration = (timestamp - enter_time).total_seconds()
                    
                    # Log exit (not an alert, but useful for analytics)
                    logger.debug(f"Track {track_id} exited zone {zone.name} after {duration:.1f}s")
                    del self.track_zones[track_id][zone_id]
        
        return events
    
    def _check_lines(self, camera_id: str, track_id: int, center: Tuple[int, int],
                     timestamp: datetime, obj_class: str) -> List[AnalyticsEvent]:
        """Check for line crossing events"""
        events = []
        
        for line_id, line in self.lines.items():
            if not line.enabled:
                continue
            
            # Check if object is close enough to line
            distance = self._calculate_distance_to_line(center, line.start, line.end)
            
            if distance < 20:  # Within 20 pixels
                # Determine crossing direction
                dx = line.end[0] - line.start[0]
                dy = line.end[1] - line.start[1]
                
                # Cross product to determine which side of line
                cross = (center[0] - line.start[0]) * dy - (center[1] - line.start[1]) * dx
                
                current_side = 'forward' if cross > 0 else 'backward'
                
                # Check if this is a new crossing
                prev_side = self.track_line_crossings[track_id].get(f"{line_id}_last_side")
                
                if prev_side and prev_side != current_side:
                    # Valid crossing detected
                    if line.direction == 'both' or line.direction == current_side:
                        event = AnalyticsEvent(
                            event_id=f"CROSS_{camera_id}_{line_id}_{track_id}_{int(timestamp.timestamp())}",
                            event_type='line_crossing',
                            camera_id=camera_id,
                            timestamp=timestamp,
                            track_id=track_id,
                            line_id=line_id,
                            confidence=0.9,
                            metadata={
                                'object_class': obj_class,
                                'line_name': line.name,
                                'direction': current_side,
                                'crossing_count': self.track_line_crossings[track_id][line_id] + 1
                            }
                        )
                        events.append(event)
                        logger.info(f"Line crossing: {line.name} by track {track_id} ({current_side})")
                        
                        self.track_line_crossings[track_id][line_id] += 1
                
                self.track_line_crossings[track_id][f"{line_id}_last_side"] = current_side
        
        return events
    
    def _check_crowd(self, camera_id: str, tracks: List[Dict], 
                     timestamp: datetime) -> List[AnalyticsEvent]:
        """Detect crowd formation based on object density"""
        events = []
        
        if len(tracks) < self.min_crowd_size:
            return events
        
        # Simple density check - count people in frame
        person_tracks = [t for t in tracks if t.get('class') == 'person']
        
        if len(person_tracks) >= self.min_crowd_size:
            # Calculate average position
            centers = [t.get('center', (0, 0)) for t in person_tracks]
            avg_x = sum(c[0] for c in centers) / len(centers)
            avg_y = sum(c[1] for c in centers) / len(centers)
            
            event = AnalyticsEvent(
                event_id=f"CROWD_{camera_id}_{int(timestamp.timestamp())}",
                event_type='crowd',
                camera_id=camera_id,
                timestamp=timestamp,
                track_id=None,
                zone_id=None,
                line_id=None,
                confidence=min(1.0, len(person_tracks) / 20),
                metadata={
                    'person_count': len(person_tracks),
                    'total_objects': len(tracks),
                    'center_point': (avg_x, avg_y)
                }
            )
            events.append(event)
            logger.warning(f"Crowd detected: {len(person_tracks)} people in camera {camera_id}")
        
        return events
    
    def _update_heatmap(self, camera_id: str, center: Tuple[int, int]):
        """Update heatmap data for a camera"""
        if camera_id not in self.heatmap_data:
            self.heatmap_data[camera_id] = np.zeros(self.heatmap_resolution, dtype=np.float32)
        
        heatmap = self.heatmap_data[camera_id]
        
        # Add Gaussian blob at center position
        x, y = int(center[0] * self.heatmap_resolution[0] / 1920), \
               int(center[1] * self.heatmap_resolution[1] / 1080)
        
        x = max(0, min(x, self.heatmap_resolution[0] - 1))
        y = max(0, min(y, self.heatmap_resolution[1] - 1))
        
        # Create small Gaussian kernel
        sigma = 5
        kernel_size = sigma * 6
        y_range = range(max(0, y - kernel_size), min(heatmap.shape[0], y + kernel_size + 1))
        x_range = range(max(0, x - kernel_size), min(heatmap.shape[1], x + kernel_size + 1))
        
        for yy in y_range:
            for xx in x_range:
                dist_sq = (xx - x)**2 + (yy - y)**2
                heatmap[yy, xx] += np.exp(-dist_sq / (2 * sigma**2))
        
        # Decay old values
        heatmap *= 0.98
    
    def get_heatmap(self, camera_id: str) -> Optional[np.ndarray]:
        """Get current heatmap for a camera"""
        return self.heatmap_data.get(camera_id)
    
    def reset_heatmap(self, camera_id: str):
        """Reset heatmap for a camera"""
        if camera_id in self.heatmap_data:
            self.heatmap_data[camera_id] = np.zeros(self.heatmap_resolution, dtype=np.float32)
    
    def get_analytics_summary(self, camera_id: Optional[str] = None, 
                              hours: int = 24) -> Dict:
        """
        Get summary statistics for analytics events
        
        Args:
            camera_id: Optional camera filter
            hours: Time window in hours
            
        Returns:
            Dictionary with analytics summary
        """
        # This would query the database in production
        # For now, return in-memory stats
        summary = {
            'total_zones': len(self.zones),
            'total_lines': len(self.lines),
            'active_tracks': len(self.track_zones),
            'zone_entries': dict(self.zone_entry_counts),
            'heatmap_cameras': list(self.heatmap_data.keys()),
            'generated_at': datetime.now().isoformat()
        }
        
        if camera_id:
            summary['camera_id'] = camera_id
            if camera_id in self.heatmap_data:
                summary['heatmap_intensity'] = float(np.max(self.heatmap_data[camera_id]))
        
        return summary
    
    def cleanup_old_tracks(self, max_age_seconds: int = 300):
        """Clean up track state for old/inactive tracks"""
        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)
        
        # Clean zone tracking
        for track_id in list(self.track_zones.keys()):
            # Remove old zone entries
            for zone_id in list(self.track_zones[track_id].keys()):
                if self.track_zones[track_id][zone_id] < cutoff:
                    del self.track_zones[track_id][zone_id]
            
            # Remove empty tracks
            if not self.track_zones[track_id]:
                del self.track_zones[track_id]
        
        # Clean line crossing history (keep counts but reset sides)
        # In production, this would be more sophisticated


# Singleton instance
analytics_engine = AdvancedAnalytics()
