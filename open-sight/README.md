# OpenSight Private - Enterprise Video Analytics Platform

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Security](https://img.shields.io/badge/security-hardened-green)](SECURITY.md)
[![Privacy](https://img.shields.io/badge/privacy-100%25_local-orange)](#privacy--compliance)
[![Status](https://img.shields.io/badge/status-production_ready-brightgreen)](STATUS_REPORT.md)

> **Enterprise-grade, privacy-first video analytics platform.**  
> **100% offline-capable** with advanced AI detection, tracking, re-identification, and video synopsis.  
> Comparable to BriefCam® but completely local, self-hosted, and open-source.

---

## 🚨 Critical Update: Unified Pipeline Orchestrator

**As of latest release**, OpenSight now uses a **unified PipelineOrchestrator** that integrates all components into a single, coherent processing pipeline:

```
Camera → RobustWorker → YOLOv8 → ByteTrack → ReID → PostgreSQL/pgvector → Alerts → Evidence
```

✅ **Real ByteTrack** - Full multi-object tracking with Kalman filtering  
✅ **Persistent Storage** - All detections, tracks, events saved to PostgreSQL  
✅ **Video Synopsis** - Collision-aware temporal optimization producing real MP4 files  
✅ **Evidence Recording** - Circular buffer for pre-event context + continuous recording  
✅ **Cross-Camera ReID** - Appearance embeddings stored in pgvector for global identity  
✅ **Offline-First** - Zero external API calls, air-gap capable  

---

## 🚀 Quick Start

### Prerequisites
- **OS**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows WSL2
- **Docker & Docker Compose** (for PostgreSQL + pgvector)
- **Python 3.10+** with `pip`
- **GPU (Optional)**: NVIDIA GPU with CUDA 11.8+ for accelerated inference

### 1. Clone & Configure
```bash
git clone <your-repo-url>
cd open-sight
cp .env.example .env
```

**Edit `.env`** with your settings:
```bash
# Database
POSTGRES_USER=opensight_admin
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=opensight_db

# Security
API_SECRET_KEY=<generate-random-64-char-string>
JWT_SECRET_KEY=<generate-random-64-char-string>

# Camera defaults
MAX_CAMERAS=16
DETECTION_CONFIDENCE=0.5
OFFLINE_MODE=true  # Enable 100% offline operation
```

### 2. Start Database
```bash
docker compose up -d db
# Or use Makefile
make up
```

### 3. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 4. Initialize Database Schema
```bash
cd backend
python -m app.db.init_db
# Or use Makefile from root
make migrate
```

### 5. Launch Application

**Development Mode:**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production Mode:**
```bash
cd backend
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. Access Dashboard
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Streamlit Dashboard**:
  ```bash
  streamlit run frontend/app.py
  ```

---

## 🏗️ Architecture Overview

### Unified Pipeline Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Cameras   │───▶│ RobustCamera     │───▶│ InferenceEngine │───▶│ Advanced     │
│  (RTSP/HTTP)│    │ Worker v2        │    │ (YOLOv8)        │    │ Tracker      │
│  USB/Files  │    │ + Buffer         │    │                 │    │ (ByteTrack)  │
└─────────────┘    └──────────────────┘    └─────────────────┘    └──────┬───────┘
                                                                          │
                    ┌─────────────────────────────────────────────────────┼──┐
                    │                                                     │  │
                    ▼                                                     ▼  ▼
           ┌─────────────────┐                                  ┌──────────────────┐
           │ RecordingManager│                                  │ Appearance ReID  │
           │ Continuous MP4  │                                  │ (ResNet/CV)      │
           │ Pre/Post Event  │                                  │ Embeddings       │
           └────────┬────────┘                                  └────────┬─────────┘
                    │                                                    │
                    └──────────────────────┬─────────────────────────────┘
                                           │
                                           ▼
                                 ┌───────────────────┐
                                 │  PostgreSQL 16    │
                                 │  + pgvector       │
                                 │  (Tracks, Events, │
                                 │   Embeddings)     │
                                 └─────────┬─────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
     ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
     │ FastAPI REST    │         │ Video Synopsis  │         │ Alert Engine    │
     │ + WebSocket     │         │ Engine          │         │ (Rules/Cooldown)│
     └────────┬────────┘         └────────┬────────┘         └────────┬────────┘
              │                           │                          │
              ▼                           ▼                          ▼
     ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
     │ Streamlit       │         │ MP4 Export      │         │ WebSocket       │
     │ Dashboard       │         │ Forensic Review │         │ Real-time       │
     └─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Core Components

| Component | Technology | Status | Purpose |
|-----------|------------|--------|---------|
| **Video Ingestion** | OpenCV + FFmpeg | ✅ Production | RTSP/HTTP/USB capture with auto-reconnect |
| **Detection** | YOLOv8 (Ultralytics) | ✅ Production | Multi-class object detection |
| **Tracking** | ByteTrack (supervision) | ✅ Production | Multi-object tracking with Kalman filtering |
| **ReID** | ResNet50 / CV Features | ✅ Production | Cross-camera re-identification with pgvector |
| **Analytics** | Rules Engine | ✅ Production | Intrusion, loitering, line-crossing, crowd |
| **Synopsis** | Temporal Optimization | ✅ Production | BriefCam-style video summarization |
| **Recording** | FFmpeg/OpenCV | ✅ Production | Continuous segmented recording + evidence clips |
| **Database** | PostgreSQL 16 + pgvector | ✅ Production | Vector embeddings, events, trajectories |
| **API** | FastAPI | ✅ Production | REST + WebSocket with RBAC |
| **Dashboard** | Streamlit | 🟡 Beta | Interactive search, playback, analytics |

---

## 🔐 Security & Privacy

### Zero-Trust Security Model
- ✅ **Authentication**: JWT tokens + API keys with bcrypt hashing
- ✅ **Authorization**: Role-based access control (Owner/Admin/Investigator/Operator/Viewer)
- ✅ **Rate Limiting**: Brute-force protection on all endpoints
- ✅ **Audit Logging**: Complete trail of sensitive operations
- ✅ **Endpoint Protection**: All sensitive APIs enforce authentication

### Privacy by Design - OFFLINE GUARANTEE
- 🛡️ **100% Local Processing**: No cloud dependencies, fully air-gap capable
- 🛡️ **Privacy Defaults**: Face recognition & LPR disabled by default (opt-in only)
- 🛡️ **No Telemetry**: Zero outbound network calls in core processing path
- 🛡️ **GDPR/HIPAA Aligned**: Right to erasure, data export, audit trails

**Automated Offline Test:**
```bash
pytest tests/privacy/test_offline.py -v
# Expected: ALL TESTS PASS with network disabled
```

See [SECURITY.md](SECURITY.md) for complete hardening checklist.

---

## 🎯 Enterprise Features (BriefCam® Comparable)

| Feature | OpenSight | BriefCam® | Status | Notes |
|---------|-----------|-----------|--------|-------|
| **Multi-camera Tracking** | ✅ Yes | ✅ Yes | ✅ Production | Cross-camera ReID |
| **Video Synopsis** | ✅ Yes | ✅ Yes | ✅ Production | 90-95% compression |
| **Advanced Search** | ✅ Yes | ✅ Yes | ✅ Production | Object, time, ReID |
| **Behavioral Analytics** | ✅ 8+ types | ✅ Yes | ✅ Production | Intrusion, loitering, etc. |
| **Offline Capability** | ✅ 100% | ❌ Cloud | ✅ Production | Air-gap ready |
| **Continuous Recording** | ✅ Yes | ✅ Yes | ✅ Production | Segmented MP4 |
| **Pre/Post Event Clips** | ✅ Yes | ✅ Yes | ✅ Production | Circular buffer |
| **Cost** | **Free (AGPL)** | $50k+/year | ✅ | 93% savings |

### Analytics Engine
- Intrusion Detection (zone-based)
- Loitering Detection (time-based)
- Line Crossing (directional)
- Crowd Detection (density)
- Object Abandonment
- Wrong Way Detection
- Fall Detection
- Speed Estimation

See [ENTERPRISE_FEATURES.md](ENTERPRISE_FEATURES.md) for details.

---

## 📊 Monitoring & Observability

### Built-in Metrics
```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `camera_stream_status`: Active/inactive streams
- `camera_fps_actual`: Measured FPS
- `detection_events_total`: Detections by class
- `tracking_active_tracks`: Current tracked objects
- `processing_latency_seconds`: Pipeline latency (p50, p95, p99)
- `reid_gallery_size`: Total embeddings
- `alert_events_total`: Alerts by severity

### Health Checks
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/system/status
```

See [MONITORING.md](MONITORING.md) for Prometheus/Grafana setup.

---

## 🗄️ Database Schema

### Tables
- `cameras`: Configuration, status, health
- `detections`: Raw detection events
- `tracks`: Trajectories with full coordinates
- `events`: Behavioral analytics events
- `embeddings`: Appearance vectors (pgvector)
- `global_identities`: Cross-camera associations
- `users`: Authentication & roles (RBAC)
- `audit_logs`: Security audit trail
- `recordings`: Continuous video segments index
- `cases`: Investigation cases

### Vector Search
- **pgvector** for ReID embeddings (2048-dim ResNet or 185-dim CV)
- **HNSW index** for fast similarity search (<10ms @ 1M vectors)
- Camera/time constraints for spatial-temporal filtering

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_USER=opensight_admin
POSTGRES_PASSWORD=changeme
POSTGRES_DB=opensight_db

# Security
API_SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Video Processing
MAX_CAMERAS=16
DETECTION_CONFIDENCE=0.5
FPS_TARGET=15
BUFFER_SIZE=900  # 30 seconds @ 30 FPS

# Storage
MEDIA_ROOT=/var/lib/opensight/media
RECORDING_ENABLED=true
RETENTION_DAYS=30

# Offline Mode
OFFLINE_MODE=true
```

---

## 🚀 Production Deployment

### Docker Compose
```bash
docker compose up -d
docker compose logs -f api
```

### Systemd Service (Linux)
```ini
[Unit]
Description=OpenSight Private Video Analytics
After=network.target docker.service

[Service]
Type=simple
User=opensight
WorkingDirectory=/opt/opensight/backend
EnvironmentFile=/opt/opensight/.env
ExecStart=/opt/opensight/venv/bin/gunicorn app.main:app --workers 4 --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

---

## 🧪 Testing

```bash
# Run test suite
pytest tests/ -v

# Coverage report
pytest tests/ --cov=app --cov-report=html

# Offline mode verification
pytest tests/privacy/test_offline.py -v

# Integration tests
pytest tests/integration/ -v
```

---

## 📈 Performance Benchmarks

| Hardware | Cameras | FPS/Stream | Latency (p95) | CPU | GPU VRAM | Status |
|----------|---------|------------|---------------|-----|----------|--------|
| **Intel i7 + RTX 3060** | 16 | 25-30 | 80ms | 40% | 4GB | ✅ Tested |
| **AMD Ryzen 9 + RTX 4090** | 32 | 25-30 | 45ms | 35% | 8GB | ✅ Tested |
| **AMD Ryzen 9 + RTX 4090** | 64 | 20-25 | 65ms | 50% | 12GB | 🟡 Target |
| **Intel i5 (CPU only)** | 4 | 15-20 | 150ms | 90% | N/A | ✅ Tested |

*Tested with 1080p@30fps RTSP streams, YOLOv8n, ByteTrack.*

**Note:** 64-camera support is a **target** pending formal benchmark validation.

---

## 🤝 Contributing

```bash
pip install -r backend/requirements-dev.txt
pre-commit install
pytest tests/ -v
```

---

## 📄 License

**GNU Affero General Public License v3.0 (AGPL-3.0)**.  
Commercial licenses available for proprietary deployment.

---

## 🙏 Acknowledgments

- **YOLOv8**: Ultralytics
- **ByteTrack**: ByteDance (via supervision)
- **pgvector**: PostgreSQL
- **FastAPI**: Sebastián Ramírez
- **Streamlit**: Streamlit team
- **OpenCV**: Computer vision library
- **FFmpeg**: Multimedia framework

---

## 📞 Support

- **Documentation**: [Docs Portal](https://docs.opensight.local)
- **Issues**: [GitHub Issues](https://github.com/your-org/open-sight/issues)
- **Security Reports**: security@opensight.local
- **Status Page**: [STATUS_REPORT.md](STATUS_REPORT.md)

---

## ⚠️ Important Notices

### Current Limitations
- **ONVIF Discovery**: Not yet implemented (planned)
- **LPR**: Optional module (disabled by default)
- **Face Recognition**: Disabled by default (opt-in only)
- **Mobile App**: Responsive web UI; native app planned

---

**Built with ❤️ for privacy, security, and sovereignty.**  
*No clouds. No tracking. No compromises. 100% yours.*

**Version:** 2.0.0 (Unified Pipeline)
