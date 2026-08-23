"""
Metrics Collector for OpenSight Private
Prometheus-compatible metrics export and system monitoring.
Enterprise-grade observability comparable to commercial VMS platforms.
"""

import time
import psutil
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Enterprise metrics collection system providing:
    - Prometheus-format metrics export
    - System resource monitoring
    - Application performance metrics
    - Custom business metrics
    """
    
    def __init__(self):
        # Counter metrics (monotonically increasing)
        self.counters: Dict[str, int] = defaultdict(int)
        self.counter_points: Dict[str, list] = defaultdict(list)
        
        # Gauge metrics (can go up/down)
        self.gauges: Dict[str, float] = {}
        self.gauge_points: Dict[str, list] = defaultdict(list)
        
        # Histogram metrics (distribution)
        self.histograms: Dict[str, list] = defaultdict(list)
        self.histogram_buckets = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        
        # Metadata
        self.start_time = time.time()
        self.labels: Dict[str, Dict[str, str]] = {}
        
        logger.info("Metrics Collector initialized")
    
    # ========== Counter Operations ==========
    
    def inc_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        self.counter_points[key].append(MetricPoint(time.time(), self.counters[key], labels or {}))
        
        # Keep only last 1000 points to prevent memory growth
        if len(self.counter_points[key]) > 1000:
            self.counter_points[key] = self.counter_points[key][-1000:]
    
    def set_counter(self, name: str, value: int, labels: Optional[Dict[str, str]] = None):
        """Set counter to specific value (use carefully)"""
        key = self._make_key(name, labels)
        self.counters[key] = value
        self.counter_points[key].append(MetricPoint(time.time(), value, labels or {}))
    
    # ========== Gauge Operations ==========
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        self.gauge_points[key].append(MetricPoint(time.time(), value, labels or {}))
        
        # Keep only last 1000 points
        if len(self.gauge_points[key]) > 1000:
            self.gauge_points[key] = self.gauge_points[key][-1000:]
    
    def inc_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a gauge"""
        key = self._make_key(name, labels)
        current = self.gauges.get(key, 0)
        self.set_gauge(name, current + value, labels)
    
    def dec_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Decrement a gauge"""
        key = self._make_key(name, labels)
        current = self.gauges.get(key, 0)
        self.set_gauge(name, current - value, labels)
    
    # ========== Histogram Operations ==========
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation in a histogram"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        
        # Keep only last 10000 observations
        if len(self.histograms[key]) > 10000:
            self.histograms[key] = self.histograms[key][-10000:]
    
    # ========== System Metrics ==========
    
    def collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.set_gauge('system_cpu_percent', cpu_percent)
            
            # Memory
            mem = psutil.virtual_memory()
            self.set_gauge('system_memory_used_bytes', mem.used)
            self.set_gauge('system_memory_available_bytes', mem.available)
            self.set_gauge('system_memory_percent', mem.percent)
            
            # Disk
            disk = psutil.disk_usage('/workspace')
            self.set_gauge('system_disk_used_bytes', disk.used)
            self.set_gauge('system_disk_free_bytes', disk.free)
            self.set_gauge('system_disk_percent', disk.percent)
            
            # Network (per interface)
            net_io = psutil.net_io_counters(pernic=True)
            for iface, counters in net_io.items():
                labels = {'interface': iface}
                self.set_gauge('system_net_bytes_sent', counters.bytes_sent, labels)
                self.set_gauge('system_net_bytes_recv', counters.bytes_recv, labels)
                self.set_gauge('system_net_packets_sent', counters.packets_sent, labels)
                self.set_gauge('system_net_packets_recv', counters.packets_recv, labels)
            
            logger.debug("System metrics collected")
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    # ========== Application Metrics ==========
    
    def record_camera_status(self, camera_id: str, active: bool):
        """Record camera stream status"""
        labels = {'camera_id': camera_id}
        self.set_gauge('opensight_camera_active', 1 if active else 0, labels)
    
    def record_detection(self, camera_id: str, object_class: str, confidence: float):
        """Record a detection event"""
        labels = {'camera_id': camera_id, 'class': object_class}
        self.inc_counter('opensight_detections_total', 1, labels)
        self.observe_histogram('opensight_detection_confidence', confidence, labels)
    
    def record_tracking(self, camera_id: str, track_count: int):
        """Record current tracking count"""
        labels = {'camera_id': camera_id}
        self.set_gauge('opensight_active_tracks', track_count, labels)
    
    def record_analytics_event(self, event_type: str, camera_id: Optional[str] = None):
        """Record an analytics event (intrusion, loitering, etc.)"""
        labels = {'event_type': event_type}
        if camera_id:
            labels['camera_id'] = camera_id
        self.inc_counter('opensight_events_total', 1, labels)
    
    def record_processing_time(self, camera_id: str, duration_ms: float):
        """Record frame processing time"""
        labels = {'camera_id': camera_id}
        self.observe_histogram('opensight_processing_time_seconds', duration_ms / 1000.0, labels)
        self.set_gauge('opensight_processing_fps', 1000.0 / duration_ms if duration_ms > 0 else 0, labels)
    
    def record_queue_depth(self, queue_name: str, depth: int):
        """Record queue depth"""
        labels = {'queue': queue_name}
        self.set_gauge('opensight_queue_depth', depth, labels)
    
    def record_database_connection(self, connections: int, max_connections: int):
        """Record database connection pool status"""
        self.set_gauge('opensight_db_connections', connections)
        self.set_gauge('opensight_db_connections_max', max_connections)
        self.set_gauge('opensight_db_connections_percent', 
                      (connections / max_connections * 100) if max_connections > 0 else 0)
    
    def record_worker_error(self, worker_type: str, error_type: Optional[str] = None):
        """Record a worker error"""
        labels = {'worker_type': worker_type}
        if error_type:
            labels['error_type'] = error_type
        self.inc_counter('opensight_worker_errors_total', 1, labels)
    
    def record_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Record an API request"""
        labels = {
            'endpoint': endpoint,
            'method': method,
            'status': str(status_code)
        }
        self.inc_counter('opensight_api_requests_total', 1, labels)
        self.observe_histogram('opensight_api_request_duration_seconds', duration_ms / 1000.0, labels)
    
    def record_storage_usage(self, storage_type: str, used_bytes: int, total_bytes: int):
        """Record storage usage (media, clips, thumbnails)"""
        labels = {'type': storage_type}
        self.set_gauge('opensight_storage_used_bytes', used_bytes, labels)
        self.set_gauge('opensight_storage_total_bytes', total_bytes, labels)
        self.set_gauge('opensight_storage_percent',
                      (used_bytes / total_bytes * 100) if total_bytes > 0 else 0, labels)
    
    # ========== Export Functions ==========
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create unique key from name and labels"""
        if not labels:
            return name
        
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format"""
        lines = []
        
        # Counters
        for key, value in self.counters.items():
            name = key.split('{')[0]
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            if '{' in key:
                # Extract labels part and format correctly
                labels_part = key.split('{', 1)[1]
                lines.append(f"{name}{{{labels_part[:-1]}}} {value}")
            else:
                lines.append(f"{name} {value}")
        
        # Gauges
        for key, value in self.gauges.items():
            name = key.split('{')[0]
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            if '{' in key:
                # Fix format: name{labels} value
                parts = key.split('{')
                metric_name = parts[0]
                labels_part = '{' + parts[1]
                lines.append(f"{metric_name}{labels_part} {value}")
            else:
                lines.append(f"{name} {value}")
        
        # Histograms
        for key, values in self.histograms.items():
            name = key.split('{')[0]
            lines.append(f"# HELP {name} Histogram metric")
            lines.append(f"# TYPE {name} histogram")
            
            if values:
                # Calculate bucket counts
                counts = {bucket: 0 for bucket in self.histogram_buckets}
                for v in values:
                    for bucket in self.histogram_buckets:
                        if v <= bucket:
                            counts[bucket] += 1
                
                # Add +Inf bucket
                counts[float('inf')] = len(values)
                
                # Output buckets
                for bucket, count in sorted(counts.items()):
                    if bucket == float('inf'):
                        bucket_str = '+Inf'
                    else:
                        bucket_str = str(bucket)
                    
                    if '{' in key:
                        parts = key.split('{')
                        metric_name = parts[0]
                        labels_part = '{' + parts[1]
                        lines.append(f'{metric_name}_bucket{{le="{bucket_str}",{labels_part[1:-1]}}} {count}')
                    else:
                        lines.append(f'{name}_bucket{{le="{bucket_str}"}} {count}')
                
                # Sum and count
                total = sum(values)
                count = len(values)
                
                if '{' in key:
                    parts = key.split('{')
                    metric_name = parts[0]
                    labels_part = '{' + parts[1]
                    lines.append(f'{metric_name}_sum{labels_part} {total}')
                    lines.append(f'{metric_name}_count{labels_part} {count}')
                else:
                    lines.append(f'{name}_sum {total}')
                    lines.append(f'{name}_count {count}')
        
        # Uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP opensight_uptime_seconds Application uptime")
        lines.append("# TYPE opensight_uptime_seconds gauge")
        lines.append(f"opensight_uptime_seconds {uptime:.2f}")
        
        return '\n'.join(lines)
    
    def get_summary(self) -> Dict:
        """Get a summary of current metrics"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histogram_count': len(self.histograms),
            'uptime_seconds': time.time() - self.start_time,
            'collected_at': datetime.now().isoformat()
        }
    
    def reset(self):
        """Reset all metrics (use with caution)"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.counter_points.clear()
        self.gauge_points.clear()
        logger.warning("All metrics reset")


# Singleton instance
metrics = MetricsCollector()
