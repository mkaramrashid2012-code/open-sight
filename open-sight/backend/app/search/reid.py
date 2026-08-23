"""Enterprise-grade Re-Identification (ReID) module for cross-camera tracking.

This module provides appearance-based person/vehicle re-identification similar to BriefCam,
enabling tracking of objects across multiple non-overlapping camera views.
All processing is local and offline - no cloud dependencies.
"""
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np
from sqlalchemy.orm import Session
from app.models.entities import Detection
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReIDFeatures:
    """Re-identification feature vector and metadata."""
    embedding: np.ndarray
    object_class: str
    track_id: int
    camera_id: str
    timestamp: datetime
    bbox: list[float]
    detection_id: Optional[str] = None
    global_track_id: Optional[int] = None

    def similarity(self, other: 'ReIDFeatures') -> float:
        """Calculate cosine similarity between embeddings."""
        if self.object_class != other.object_class:
            return 0.0

        norm1 = np.linalg.norm(self.embedding)
        norm2 = np.linalg.norm(other.embedding)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(self.embedding, other.embedding) / (norm1 * norm2))


class ReIDEmbedder:
    """
    Generate appearance embeddings for re-identification using multi-modal features.
    
    Combines color histograms, HOG, LBP texture, edge density, and color moments
    for robust re-identification without neural network dependencies.
    All processing runs locally on CPU/GPU/MPS.
    """

    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim
        self._initialized = False
        self._device = settings.model_device

    def initialize(self):
        """Initialize the embedder."""
        if self._initialized:
            return
        logger.info(f"ReID embedder initialized (dim={self.embedding_dim}, device={self._device})")
        self._initialized = True

    def extract(self, frame: np.ndarray, bbox: list[float], object_class: str) -> Optional[np.ndarray]:
        """Extract appearance embedding from a detection crop."""
        if not self._initialized:
            self.initialize()

        try:
            x1, y1, x2, y2 = map(int, bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

            if x2 <= x1 or y2 <= y1:
                return None

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return None

            # Convert BGR to RGB
            if len(crop.shape) == 3 and crop.shape[2] == 3:
                import cv2
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            else:
                import cv2
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)

            embedding = self._extract_multimodal_features(crop_rgb, object_class)

            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(f"Error extracting ReID features: {e}", exc_info=True)
            return None

    def _extract_multimodal_features(self, crop: np.ndarray, object_class: str) -> np.ndarray:
        """Extract multi-modal features for robust re-identification."""
        import cv2
        
        features_list = []
        target_size = (64, 128)
        resized = cv2.resize(crop, target_size, interpolation=cv2.INTER_AREA)
        
        # 1. Color histograms with spatial pyramid
        hist_full = self._color_histogram(resized, bins=32)
        features_list.append(hist_full)
        
        h, w = resized.shape[:2]
        mid_h, mid_w = h // 2, w // 2
        
        for quadrant in [
            resized[0:mid_h, 0:mid_w],
            resized[0:mid_h, mid_w:w],
            resized[mid_h:h, 0:mid_w],
            resized[mid_h:h, mid_w:w],
        ]:
            if quadrant.size > 0:
                features_list.append(self._color_histogram(quadrant, bins=16))
        
        # 2. HOG features
        gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
        features_list.append(self._compute_hog(gray, cell_size=(8, 8)))
        
        # 3. LBP texture
        features_list.append(self._compute_lbp(gray))
        
        # 4. Edge density
        features_list.append(self._compute_edge_density(gray))
        
        # 5. Color moments
        features_list.append(self._compute_color_moments(resized))
        
        combined = np.concatenate(features_list)
        
        if len(combined) < self.embedding_dim:
            combined = np.pad(combined, (0, self.embedding_dim - len(combined)))
        else:
            combined = combined[:self.embedding_dim]

        return combined

    def _color_histogram(self, image: np.ndarray, bins: int = 32) -> np.ndarray:
        """Compute normalized color histogram."""
        import cv2
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        hist = np.concatenate([
            cv2.calcHist([image], [i], None, [bins], [0, 256]).flatten()
            for i in range(3)
        ])
        
        total = hist.sum()
        if total > 0:
            hist = hist / total
        return hist

    def _compute_hog(self, image: np.ndarray, cell_size: tuple = (8, 8)) -> np.ndarray:
        """Compute HOG features."""
        import cv2
        if image.shape[0] < cell_size[1] or image.shape[1] < cell_size[0]:
            image = cv2.resize(image, (cell_size[0] * 4, cell_size[1] * 4))
        
        hog = cv2.HOGDescriptor(
            (image.shape[1], image.shape[0]),
            (cell_size[0] * 2, cell_size[1] * 2),
            (cell_size[0], cell_size[1]),
            cell_size, 9
        )
        features = hog.compute(image)
        return features.flatten() if features is not None else np.zeros(81)

    def _compute_lbp(self, image: np.ndarray) -> np.ndarray:
        """Compute Local Binary Pattern features."""
        import cv2
        resized = cv2.resize(image, (32, 64))
        lbp_image = np.zeros_like(resized, dtype=np.uint8)
        radius, n_points = 1, 8
        
        for i in range(radius, resized.shape[0] - radius):
            for j in range(radius, resized.shape[1] - radius):
                center = resized[i, j]
                code = 0
                for k in range(n_points):
                    angle = 2 * np.pi * k / n_points
                    ni = int(i + radius * np.sin(angle))
                    nj = int(j + radius * np.cos(angle))
                    if resized[ni, nj] >= center:
                        code |= (1 << k)
                lbp_image[i, j] = code
        
        hist = cv2.calcHist([lbp_image], [0], None, [256], [0, 256]).flatten()
        total = hist.sum()
        return hist / total if total > 0 else hist

    def _compute_edge_density(self, image: np.ndarray) -> np.ndarray:
        """Compute edge density features."""
        import cv2
        edges = cv2.Canny(image, 50, 150)
        h, w = edges.shape
        
        densities = [
            np.sum(edges[i*h//2:(i+1)*h//2, j*w//2:(j+1)*w//2] > 0) / ((h*w)//4)
            for i in range(2) for j in range(2)
        ]
        densities.append(np.sum(edges > 0) / (h * w))
        return np.array(densities)

    def _compute_color_moments(self, image: np.ndarray) -> np.ndarray:
        """Compute color moments."""
        moments = []
        for i in range(3):
            channel = image[:, :, i].flatten()
            mean = np.mean(channel)
            std = np.std(channel)
            skewness = np.mean(((channel - mean) / std) ** 3) if std > 0 else 0.0
            moments.extend([mean / 255.0, std / 255.0, skewness])
        return np.array(moments)


class CrossCameraTracker:
    """Track objects across multiple cameras using ReID embeddings."""

    def __init__(self, db_session_factory, similarity_threshold: float = 0.65):
        self.db_session_factory = db_session_factory
        self.similarity_threshold = similarity_threshold
        self.embedder = ReIDEmbedder()
        self._track_gallery: dict[int, ReIDFeatures] = {}
        self._cache_max_age_seconds = 7200
        self._next_global_id = 1
        logger.info(f"Cross-camera tracker initialized (threshold={similarity_threshold})")

    def match_or_create_track(self, detection: Detection, frame: np.ndarray, db: Session) -> int:
        """Match detection to existing global track or create new one."""
        embedding = self.embedder.extract(frame, detection.bbox, detection.object_class)
        
        if embedding is None:
            return self._create_new_track(detection, np.zeros(self.embedder.embedding_dim))
        
        query_features = ReIDFeatures(
            embedding=embedding,
            object_class=detection.object_class,
            track_id=detection.track_id or 0,
            camera_id=str(detection.camera_id),
            timestamp=detection.timestamp,
            bbox=detection.bbox,
            detection_id=str(detection.id),
        )
        
        self._clean_gallery()
        
        best_match_id, best_similarity = None, 0.0
        for global_id, gallery_features in self._track_gallery.items():
            if gallery_features.object_class != query_features.object_class:
                continue
            similarity = query_features.similarity(gallery_features)
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match_id = global_id
        
        if best_match_id is not None:
            self._update_track(best_match_id, query_features, detection)
            logger.debug(f"Matched to global track {best_match_id} (similarity={best_similarity:.3f})")
            return best_match_id
        
        return self._create_new_track(detection, embedding)

    def _create_new_track(self, detection: Detection, embedding: np.ndarray) -> int:
        """Create a new global track ID."""
        global_id = self._next_global_id
        self._next_global_id += 1
        
        self._track_gallery[global_id] = ReIDFeatures(
            embedding=embedding.copy(),
            object_class=detection.object_class,
            track_id=detection.track_id or 0,
            camera_id=str(detection.camera_id),
            timestamp=detection.timestamp,
            bbox=detection.bbox,
            detection_id=str(detection.id),
            global_track_id=global_id,
        )
        logger.debug(f"Created new global track {global_id}")
        return global_id

    def _update_track(self, global_id: int, new_features: ReIDFeatures, detection: Detection):
        """Update an existing track with exponential moving average."""
        existing = self._track_gallery.get(global_id)
        if existing is None:
            return
        
        alpha = 0.3
        updated_embedding = alpha * new_features.embedding + (1 - alpha) * existing.embedding
        norm = np.linalg.norm(updated_embedding)
        if norm > 0:
            updated_embedding = updated_embedding / norm
        
        self._track_gallery[global_id] = ReIDFeatures(
            embedding=updated_embedding,
            object_class=existing.object_class,
            track_id=new_features.track_id,
            camera_id=str(detection.camera_id),
            timestamp=detection.timestamp,
            bbox=new_features.bbox,
            detection_id=str(detection.id),
            global_track_id=global_id,
        )

    def _clean_gallery(self):
        """Remove stale entries."""
        now = datetime.now(timezone.utc)
        to_remove = [
            gid for gid, f in self._track_gallery.items()
            if (now - f.timestamp).total_seconds() > self._cache_max_age_seconds
        ]
        for gid in to_remove:
            del self._track_gallery[gid]
        if to_remove:
            logger.debug(f"Cleaned {len(to_remove)} stale tracks")

    def search_similar_tracks(
        self, query_frame: np.ndarray, query_bbox: list[float], object_class: str,
        max_results: int = 20, time_window_hours: Optional[int] = None,
        camera_id: Optional[str] = None,
    ) -> list[dict]:
        """Search for similar tracks based on appearance."""
        query_embedding = self.embedder.extract(query_frame, query_bbox, object_class)
        if query_embedding is None:
            return []
        
        query_features = ReIDFeatures(
            embedding=query_embedding, object_class=object_class, track_id=0,
            camera_id=camera_id or "", timestamp=datetime.now(timezone.utc),
            bbox=query_bbox,
        )
        
        results = []
        now = datetime.now(timezone.utc)
        
        for global_id, gf in self._track_gallery.items():
            if gf.object_class != object_class:
                continue
            if camera_id and gf.camera_id != camera_id:
                continue
            if time_window_hours:
                age_hours = (now - gf.timestamp).total_seconds() / 3600
                if age_hours > time_window_hours:
                    continue
            
            similarity = query_features.similarity(gf)
            if similarity >= self.similarity_threshold:
                results.append({
                    "global_track_id": global_id,
                    "camera_id": gf.camera_id,
                    "local_track_id": gf.track_id,
                    "timestamp": gf.timestamp.isoformat(),
                    "similarity": float(similarity),
                    "object_class": gf.object_class,
                })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]

    def get_all_active_tracks(self) -> list[dict]:
        """Get all active global tracks."""
        self._clean_gallery()
        return [
            {
                "global_track_id": gid,
                "object_class": f.object_class,
                "camera_id": f.camera_id,
                "first_seen": f.timestamp.isoformat(),
                "detection_id": f.detection_id,
            }
            for gid, f in self._track_gallery.items()
        ]


# Global instance
_cross_camera_tracker: Optional[CrossCameraTracker] = None


def init_cross_camera_tracker(db_session_factory) -> CrossCameraTracker:
    """Initialize the global cross-camera tracker."""
    global _cross_camera_tracker
    logger.info("Initializing cross-camera ReID tracker...")
    _cross_camera_tracker = CrossCameraTracker(db_session_factory)
    return _cross_camera_tracker


def get_cross_camera_tracker() -> Optional[CrossCameraTracker]:
    """Get the global cross-camera tracker."""
    return _cross_camera_tracker


# Alias for backward compatibility
ReIDService = CrossCameraTracker
