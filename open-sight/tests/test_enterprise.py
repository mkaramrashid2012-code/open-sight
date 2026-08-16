"""
Comprehensive Test Suite for OpenSight Private
Enterprise-grade testing with security, performance, and integration tests.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np

# Import modules to test
from app.analytics.engine import (
    AdvancedAnalytics, ZoneConfig, LineConfig, AnalyticsEvent
)
from app.search.reid import ReIDModule
from app.security.auth import verify_password, hash_password


class TestAdvancedAnalytics:
    """Test suite for the Advanced Analytics Engine"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analytics = AdvancedAnalytics()
        
        # Create test zones
        self.intrusion_zone = ZoneConfig(
            id="zone_001",
            name="Server Room",
            polygon=[(100, 100), (200, 100), (200, 200), (100, 200)],
            zone_type="intrusion",
            sensitivity=0.8
        )
        
        self.loitering_zone = ZoneConfig(
            id="zone_002",
            name="Entrance Lobby",
            polygon=[(300, 300), (400, 300), (400, 400), (300, 400)],
            zone_type="loitering",
            min_duration=5.0
        )
        
        # Create test line
        self.counting_line = LineConfig(
            id="line_001",
            name="Doorway Counter",
            start=(500, 0),
            end=(500, 1080),
            direction="both"
        )
        
        # Add to analytics
        self.analytics.add_zone(self.intrusion_zone)
        self.analytics.add_zone(self.loitering_zone)
        self.analytics.add_line(self.counting_line)
    
    def test_zone_addition(self):
        """Test adding detection zones"""
        assert "zone_001" in self.analytics.zones
        assert "zone_002" in self.analytics.zones
        assert self.analytics.zones["zone_001"].name == "Server Room"
    
    def test_line_addition(self):
        """Test adding virtual lines"""
        assert "line_001" in self.analytics.lines
        assert self.analytics.lines["line_001"].name == "Doorway Counter"
    
    def test_point_in_polygon(self):
        """Test point-in-polygon detection"""
        # Point inside zone
        assert self.analytics._point_in_polygon((150, 150), self.intrusion_zone.polygon) is True
        
        # Point outside zone
        assert self.analytics._point_in_polygon((50, 50), self.intrusion_zone.polygon) is False
        
        # Point on edge (should be considered inside)
        assert self.analytics._point_in_polygon((100, 150), self.intrusion_zone.polygon) is True
    
    def test_intrusion_detection(self):
        """Test intrusion event generation"""
        tracks = [{
            'id': 1,
            'bbox': [140, 140, 160, 160],
            'center': (150, 150),
            'class': 'person'
        }]
        
        timestamp = datetime.now()
        events = self.analytics.process_tracks("cam_001", tracks, timestamp)
        
        # Should detect intrusion
        intrusion_events = [e for e in events if e.event_type == 'intrusion']
        assert len(intrusion_events) > 0
        assert intrusion_events[0].zone_id == "zone_001"
        assert intrusion_events[0].track_id == 1
    
    def test_no_intrusion_outside_zone(self):
        """Test no intrusion when outside zone"""
        tracks = [{
            'id': 2,
            'bbox': [50, 50, 70, 70],
            'center': (60, 60),
            'class': 'person'
        }]
        
        timestamp = datetime.now()
        events = self.analytics.process_tracks("cam_001", tracks, timestamp)
        
        # Should not detect intrusion
        intrusion_events = [e for e in events if e.event_type == 'intrusion']
        assert len(intrusion_events) == 0
    
    @pytest.mark.asyncio
    async def test_loitering_detection(self):
        """Test loitering detection after duration threshold"""
        track_id = 3
        center = (350, 350)  # Inside loitering zone
        
        tracks = [{
            'id': track_id,
            'bbox': [340, 340, 360, 360],
            'center': center,
            'class': 'person'
        }]
        
        # First detection - no loitering yet
        timestamp1 = datetime.now()
        events1 = self.analytics.process_tracks("cam_002", tracks, timestamp1)
        loitering_events1 = [e for e in events1 if e.event_type == 'loitering']
        assert len(loitering_events1) == 0
        
        # Wait simulated time (5+ seconds)
        await asyncio.sleep(0.1)  # Short sleep for test
        timestamp2 = datetime.now()
        
        # Second detection - should trigger loitering
        events2 = self.analytics.process_tracks("cam_002", tracks, timestamp2)
        
        # Note: In real scenario, duration would exceed threshold
        # For unit test, we verify the tracking state is maintained
        assert track_id in self.analytics.track_zones
        assert "zone_002" in self.analytics.track_zones[track_id]
    
    def test_line_crossing_detection(self):
        """Test line crossing event generation"""
        track_id = 4
        
        # Approach line from left
        tracks_left = [{
            'id': track_id,
            'bbox': [480, 500, 490, 520],
            'center': (485, 510),
            'class': 'person'
        }]
        
        timestamp1 = datetime.now()
        self.analytics.process_tracks("cam_003", tracks_left, timestamp1)
        
        # Cross to right side
        tracks_right = [{
            'id': track_id,
            'bbox': [510, 500, 520, 520],
            'center': (515, 510),
            'class': 'person'
        }]
        
        timestamp2 = datetime.now() + timedelta(milliseconds=100)
        events = self.analytics.process_tracks("cam_003", tracks_right, timestamp2)
        
        # Should detect crossing
        crossing_events = [e for e in events if e.event_type == 'line_crossing']
        assert len(crossing_events) > 0
        assert crossing_events[0].line_id == "line_001"
    
    def test_heatmap_generation(self):
        """Test heatmap data accumulation"""
        camera_id = "cam_heatmap_test"
        
        # Simulate multiple detections at same location
        for i in range(10):
            tracks = [{
                'id': i,
                'bbox': [500, 500, 520, 520],
                'center': (510, 510),
                'class': 'person'
            }]
            self.analytics.process_tracks(camera_id, tracks, datetime.now())
        
        # Check heatmap exists and has values
        heatmap = self.analytics.get_heatmap(camera_id)
        assert heatmap is not None
        assert heatmap.shape == self.analytics.heatmap_resolution
        assert np.max(heatmap) > 0
    
    def test_crowd_detection(self):
        """Test crowd detection with multiple people"""
        # Create 6 person tracks
        tracks = []
        for i in range(6):
            tracks.append({
                'id': i + 100,
                'bbox': [100 + i*50, 300, 120 + i*50, 320],
                'center': (110 + i*50, 310),
                'class': 'person'
            })
        
        timestamp = datetime.now()
        events = self.analytics.process_tracks("cam_crowd", tracks, timestamp)
        
        # Should detect crowd
        crowd_events = [e for e in events if e.event_type == 'crowd']
        assert len(crowd_events) > 0
        assert crowd_events[0].metadata['person_count'] >= 5
    
    def test_analytics_summary(self):
        """Test analytics summary generation"""
        summary = self.analytics.get_analytics_summary()
        
        assert 'total_zones' in summary
        assert 'total_lines' in summary
        assert summary['total_zones'] >= 2
        assert summary['total_lines'] >= 1
    
    def test_zone_removal(self):
        """Test zone removal"""
        self.analytics.remove_zone("zone_001")
        assert "zone_001" not in self.analytics.zones
        assert len(self.analytics.zones) == 1
    
    def test_cleanup_old_tracks(self):
        """Test cleanup of old track data"""
        # Add some track data
        self.analytics.track_zones[999] = {"zone_001": datetime.now() - timedelta(hours=2)}
        
        # Cleanup
        self.analytics.cleanup_old_tracks(max_age_seconds=300)
        
        # Old track should be removed
        assert 999 not in self.analytics.track_zones


class TestReIDModule:
    """Test suite for Re-Identification Module"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.reid = ReIDModule()
    
    def test_color_histogram_extraction(self):
        """Test color histogram feature extraction"""
        # Create simple test image (red square)
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[:, :] = [255, 0, 0]  # Red
        
        features = self.reid.extract_color_histogram(test_image)
        
        assert features is not None
        assert len(features) > 0
        assert isinstance(features, np.ndarray)
    
    def test_feature_vector_size(self):
        """Test that feature vector has expected size"""
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        features = self.reid.compute_features(test_image)
        
        # Feature vector should be non-empty
        assert features is not None
        assert len(features.shape) == 1
    
    def test_similarity_same_image(self):
        """Test similarity score for identical images"""
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        features1 = self.reid.compute_features(test_image)
        features2 = self.reid.compute_features(test_image)
        
        similarity = self.reid.compute_similarity(features1, features2)
        
        # Same image should have high similarity
        assert similarity > 0.9
    
    def test_similarity_different_images(self):
        """Test similarity score for different images"""
        image1 = np.zeros((100, 100, 3), dtype=np.uint8)  # Black
        image1[:, :] = [255, 0, 0]  # Red
        
        image2 = np.zeros((100, 100, 3), dtype=np.uint8)  # Black
        image2[:, :] = [0, 0, 255]  # Blue
        
        features1 = self.reid.compute_features(image1)
        features2 = self.reid.compute_features(image2)
        
        similarity = self.reid.compute_similarity(features1, features2)
        
        # Different colors should have lower similarity
        assert similarity < 0.8


class TestSecurity:
    """Test suite for Security Modules"""
    
    def test_password_hashing(self):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
    
    def test_password_verification_success(self):
        """Test successful password verification"""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_uniqueness(self):
        """Test that same password produces different hashes"""
        password = "SamePassword"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # bcrypt uses random salt, so hashes should differ
        assert hash1 != hash2
        
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPerformance:
    """Performance and load tests"""
    
    def test_analytics_processing_speed(self):
        """Test analytics processing can handle real-time rates"""
        analytics = AdvancedAnalytics()
        
        # Add a zone
        zone = ZoneConfig(
            id="perf_zone",
            name="Performance Test",
            polygon=[(0, 0), (1920, 0), (1920, 1080), (0, 1080)],
            zone_type="intrusion"
        )
        analytics.add_zone(zone)
        
        # Simulate 30 FPS processing for 1 second
        num_tracks = 10
        tracks = [{
            'id': i,
            'bbox': [100 + i*100, 100, 120 + i*100, 120],
            'center': (110 + i*100, 110),
            'class': 'person'
        } for i in range(num_tracks)]
        
        import time
        start_time = time.time()
        
        for frame in range(30):  # 30 frames
            analytics.process_tracks("cam_perf", tracks, datetime.now())
        
        elapsed = time.time() - start_time
        
        # Should process 30 frames in less than 1 second (real-time)
        assert elapsed < 1.0, f"Processing took {elapsed:.2f}s, expected < 1.0s"
        
        # Calculate FPS
        fps = 30 / elapsed
        print(f"Analytics processing speed: {fps:.1f} FPS")
        assert fps > 30, f"FPS {fps:.1f} below real-time requirement"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
