# OpenSight Private - Monitoring & Observability Guide

## Enterprise-Grade Monitoring Stack

This guide covers comprehensive monitoring, alerting, and observability for production deployments.

---

## 1. Built-in Health Endpoints

### System Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "workers": "healthy",
    "storage": "healthy"
  },
  "metrics": {
    "active_cameras": 8,
    "processing_fps": 24.5,
    "queue_depth": 12,
    "memory_usage_mb": 2048
  }
}
```

### Detailed Metrics Endpoint
```bash
curl http://localhost:8000/metrics
```

**Returns Prometheus-format metrics:**
```
# HELP opensight_cameras_active Number of active camera streams
# TYPE opensight_cameras_active gauge
opensight_cameras_active 8

# HELP opensight_processing_fps Current processing frames per second
# TYPE opensight_processing_fps gauge
opensight_processing_fps 24.5

# HELP opensight_queue_depth Current event queue depth
# TYPE opensight_queue_depth gauge
opensight_queue_depth 12

# HELP opensight_memory_usage_bytes Memory usage in bytes
# TYPE opensight_memory_usage_bytes gauge
opensight_memory_usage_bytes 2147483648

# HELP opensight_detections_total Total number of detections
# TYPE opensight_detections_total counter
opensight_detections_total 145892

# HELP opensight_events_total Total number of analytics events
# TYPE opensight_events_total counter
opensight_events_total 3421
```

---

## 2. Structured Logging

### Log Format (JSON)
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "app.workers.video_processor",
  "message": "Frame processed successfully",
  "context": {
    "camera_id": "cam_001",
    "frame_id": 15234,
    "processing_time_ms": 42.5,
    "detections": 3,
    "tracks": 2
  },
  "trace_id": "abc123def456",
  "span_id": "xyz789"
}
```

### Log Levels
- **DEBUG**: Detailed processing information
- **INFO**: Normal operations (frame processing, events)
- **WARNING**: Recoverable issues (reconnection attempts)
- **ERROR**: Failures requiring attention
- **CRITICAL**: System-wide failures

### Log Aggregation Setup

#### Option A: ELK Stack (Elasticsearch, Logstash, Kibana)
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

#### Option B: Grafana Loki (Lightweight)
```yaml
# docker-compose.loki.yml
version: '3.8'
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log/opensight:/var/log/opensight
      - ./promtail/config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

---

## 3. Prometheus + Grafana Integration

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'opensight'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']  # Node exporter
```

### Key Metrics to Monitor

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `opensight_cameras_active` | Gauge | Active camera streams | < expected count |
| `opensight_processing_fps` | Gauge | Processing speed | < 15 FPS |
| `opensight_queue_depth` | Gauge | Pending events | > 1000 |
| `opensight_memory_usage_bytes` | Gauge | Memory consumption | > 80% available |
| `opensight_detections_total` | Counter | Total detections | - |
| `opensight_events_total` | Counter | Analytics events | - |
| `opensight_worker_errors_total` | Counter | Worker errors | > 10/min |
| `opensight_database_connections` | Gauge | DB connections | > 80% pool |

### Grafana Dashboard Panels

**Recommended Panels:**
1. Camera Status Overview (status lights)
2. Processing FPS over time (line chart)
3. Event rate by type (stacked area)
4. Memory & CPU usage (dual axis)
5. Queue depth trend (line chart)
6. Error rate heatmap
7. Detection breakdown by class (pie chart)
8. Storage usage (gauge)

---

## 4. Alerting Rules

### Prometheus Alert Rules
```yaml
# alerts.yml
groups:
  - name: opensight_alerts
    interval: 30s
    rules:
      - alert: CameraOffline
        expr: opensight_cameras_active < 8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Camera offline detected"
          description: "Only {{ $value }} cameras active (expected 8)"

      - alert: LowProcessingSpeed
        expr: opensight_processing_fps < 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low processing FPS"
          description: "Processing at {{ $value }} FPS"

      - alert: HighQueueDepth
        expr: opensight_queue_depth > 1000
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Event queue backing up"
          description: "Queue depth: {{ $value }}"

      - alert: HighMemoryUsage
        expr: opensight_memory_usage_bytes / (1024*1024*1024) > 7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Using {{ $value }} GB RAM"

      - alert: WorkerErrors
        expr: rate(opensight_worker_errors_total[5m]) > 0.5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High worker error rate"
          description: "{{ $value }} errors/sec"
```

### Alertmanager Configuration
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'opensight-alerts@company.com'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'email-notifications'
  
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
    - match:
        severity: warning
      receiver: 'slack-warnings'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'security-team@company.com'
        
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
      
  - name: 'slack-warnings'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK'
        channel: '#security-alerts'
```

---

## 5. Distributed Tracing (Optional)

### Jaeger Integration
```python
# Add to backend/app/main.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracing
provider = TracerProvider()
processor = BatchSpanProcessor(JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

### Run Jaeger
```bash
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

Access UI: http://localhost:16686

---

## 6. Performance Profiling

### Built-in Profiling Endpoint
```bash
# Enable profiling (dev/staging only)
curl http://localhost:8000/debug/profiler?duration=30
```

### Manual Profiling
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... run workload ...

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(20)
```

---

## 7. Automated Health Checks

### Cron-based Monitoring
```bash
# /etc/cron.d/opensight-health
*/5 * * * * root /workspace/open-sight/scripts/health_check.sh >> /var/log/opensight/health.log 2>&1
```

### Systemd Service Watchdog
```ini
# /etc/systemd/system/opensight.service
[Service]
...
WatchdogSec=30
Restart=on-failure
RestartSec=10
```

Enable watchdog in app:
```python
from sdnotify import SystemdNotifier
sd = SystemdNotifier()
sd.notify("WATCHDOG=1")
```

---

## 8. Audit Trail & Compliance

### Audit Log Queries
```sql
-- Recent security events
SELECT timestamp, event_type, user_id, resource, action
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Failed login attempts
SELECT user_id, ip_address, COUNT(*) as attempts
FROM audit_logs
WHERE event_type = 'login_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_id, ip_address
HAVING COUNT(*) > 5;

-- Data access patterns
SELECT resource_type, COUNT(*) as accesses
FROM audit_logs
WHERE event_type = 'data_access'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY resource_type;
```

### Export Audit Logs
```bash
# CSV export for compliance
psql -h localhost -U opensight -d opensight_db -c \
"COPY (SELECT * FROM audit_logs WHERE timestamp > NOW() - INTERVAL '90 days') TO STDOUT WITH CSV HEADER" \
> audit_export_$(date +%Y%m%d).csv
```

---

## 9. Dashboard Examples

### Grafana JSON Import
Pre-built dashboard available at: `monitoring/grafana-dashboard.json`

**Import via Grafana UI:**
1. Dashboards → Import
2. Upload JSON file
3. Select Prometheus data source
4. Click Import

---

## 10. Incident Response Playbook

### Camera Offline
1. Check physical network connectivity
2. Verify RTSP stream accessibility: `vlc rtsp://camera-ip/stream`
3. Check worker logs: `journalctl -u opensight -f`
4. Restart camera worker via API: `POST /api/v1/cameras/{id}/restart`
5. If persistent, check camera hardware

### High Queue Depth
1. Scale workers: increase `MAX_WORKERS` in config
2. Check database performance: `pg_stat_activity`
3. Reduce detection confidence threshold temporarily
4. Consider adding GPU acceleration

### Memory Pressure
1. Identify memory-heavy cameras via metrics
2. Reduce resolution/FPS for non-critical cameras
3. Increase `FRAME_BUFFER_SIZE` cleanup frequency
4. Add swap space as temporary measure
5. Consider horizontal scaling

### Database Connection Issues
1. Check connection pool: `SELECT * FROM pg_stat_activity`
2. Kill idle connections if needed
3. Verify `max_connections` in PostgreSQL config
4. Check disk space: `df -h`
5. Review slow query log

---

## Quick Start Monitoring Stack

```bash
# Start full monitoring stack
cd /workspace/open-sight
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access dashboards
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
echo "Health Check: http://localhost:8000/health"
```

---

**Next Steps:**
1. Configure alerting channels (email, Slack, PagerDuty)
2. Customize alert thresholds for your environment
3. Set up log rotation (`/etc/logrotate.d/opensight`)
4. Schedule regular backup verification
5. Document runbook procedures for common incidents
