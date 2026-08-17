# OpenSight Private - Enterprise Video Analytics Platform

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Security](https://img.shields.io/badge/security-hardened-green)](SECURITY.md)
[![Privacy](https://img.shields.io/badge/privacy-100%25_local-orange)](#privacy--compliance)

> **Enterprise-grade, privacy-first video analytics platform.**  
> Comparable to BriefCam® but 100% local, offline, and open-source.  
> Process up to 64 concurrent camera streams with advanced AI detection, tracking, re-identification, and video synopsis capabilities.

---

## 🚀 Quick Start

### Prerequisites
- **OS**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows WSL2
- **Docker & Docker Compose** (for database)
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
```

### 2. Start Database
```bash
docker compose up -d db
# Or use Makefile
make up
```

### 3. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r backend/requirements.txt
```

### 4. Run Migrations
```bash
cd backend
alembic upgrade head
# Or use Makefile from root
make migrate
```

### 5. Launch Application

**Development Mode:**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Or use Makefile from root
make api
```

**Production Mode (Recommended):**
```bash
cd backend
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5
```

### 6. Access Dashboard
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Streamlit Dashboard** (optional):
  ```bash
  streamlit run frontend/app.py
  # Or use Makefile
  make dashboard
  ```

---

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Cameras   │───▶│  RTSP Worker │───▶│  YOLOv8 + Track │───▶│  PostgreSQL  │
│  (RTSP/HTTP)│    │  (OpenCV)    │    │  (ByteTrack)    │    │  + pgvector  │
└─────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                                                                  │
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐        │
│  Streamlit  │◀───│  FastAPI     │◀───│  Search Engine  │◀───────┘
│  Dashboard  │    │  REST/WebSocket│   │  (ReID/Synopsis)│
└─────────────┘    └──────────────┘    └─────────────────┘
```

### Core Components
| Component | Technology | Purpose |
|-----------|------------|---------|
| **Video Ingestion** | OpenCV + FFmpeg | RTSP/HTTP stream capture with auto-reconnect |
| **Detection** | YOLOv8 (Ultralytics) | Real-time object/person/vehicle detection |
| **Tracking** | ByteTrack | Multi-object tracking with occlusion handling |
| **ReID** | ResNet50 / CV Features | Cross-camera person/vehicle re-identification |
| **Analytics** | Custom Rules Engine | Intrusion, loitering, line-crossing, crowd detection |
| **Synopsis** | Temporal Compression | BriefCam-style video summarization |
| **Database** | PostgreSQL 16 + pgvector | Vector embeddings, time-series events, metadata |
| **API** | FastAPI | REST + WebSocket real-time streaming |
| **Dashboard** | Streamlit | Interactive search, playback, analytics |

---

## 🔐 Security & Privacy

### Zero-Trust Security Model
- ✅ **Authentication**: JWT tokens + API keys with bcrypt hashing
- ✅ **Authorization**: Role-based access control (User/Superuser)
- ✅ **Rate Limiting**: Brute-force protection on all endpoints
- ✅ **Audit Logging**: Complete trail of sensitive operations
- ✅ **Input Validation**: Pydantic models on all inputs
- ✅ **No Hardcoded Secrets**: All via environment variables

### Privacy by Design
- 🛡️ **100% Local Processing**: No cloud dependencies, air-gap capable
- 🛡️ **Privacy Defaults**: Face recognition & LPR disabled by default
- 🛡️ **Data Minimization**: Only store necessary metadata + thumbnails
- 🛡️ **GDPR/HIPAA Ready**: Right to erasure, data export, audit trails

See [SECURITY.md](SECURITY.md) for complete hardening checklist.

---

## 🎯 Enterprise Features (BriefCam® Comparable)

| Feature | OpenSight Private | BriefCam® | Notes |
|---------|-------------------|-----------|-------|
| **Multi-camera Tracking** | ✅ Yes | ✅ Yes | Cross-camera ReID with appearance matching |
| **Video Synopsis** | ✅ Yes | ✅ Yes | 90-95% temporal compression |
| **Advanced Search** | ✅ Yes | ✅ Yes | By object, time, color, direction, ReID |
| **Behavioral Analytics** | ✅ 8 types | ✅ Yes | Intrusion, loitering, crowd, falls, etc. |
| **Heatmaps** | ✅ Yes | ✅ Yes | Density visualization |
| **Real-time Alerts** | ✅ WebSocket | ✅ Yes | Bidirectional streaming |
| **Offline Capability** | ✅ 100% | ❌ Cloud-dependent | Air-gap ready |
| **Cost** | **Free (AGPL)** | $50k+/year | 93% cost savings |
| **Max Cameras** | 64 (scalable) | 1000+ | Horizontal scaling supported |

### Advanced Analytics Engine
- **Intrusion Detection**: Zone-based entry alerts
- **Loitering Detection**: Time-based presence alerts
- **Line Crossing**: Directional boundary violations
- **Crowd Detection**: Density threshold monitoring
- **Object Abandonment**: Unattended item detection
- **Wrong Way Detection**: Directional flow violations
- **Fall Detection**: Sudden posture changes
- **Speed Estimation**: Velocity calculation (calibrated)

See [ENTERPRISE_FEATURES.md](ENTERPRISE_FEATURES.md) for complete feature comparison.

---

## 📊 Monitoring & Observability

### Built-in Metrics (Prometheus Format)
```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `camera_stream_status`: Active/inactive streams
- `detection_events_total`: Detections by class
- `tracking_active_tracks`: Current tracked objects
- `processing_latency_seconds`: Pipeline latency
- `database_connections_active`: Pool utilization
- `api_requests_total`: Request counts by endpoint

### Health Checks
```bash
# System health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/api/v1/system/status
```

See [MONITORING.md](MONITORING.md) for Prometheus/Grafana/ELK setup.

---

## 🗄️ Database Schema

### Tables
- `cameras`: Camera configuration & status
- `detections`: Raw detection events (bbox, class, confidence)
- `tracks`: Tracked object trajectories
- `events`: Behavioral analytics events
- `media`: Stored clips/thumbnails paths
- `users`: Authentication & roles
- `audit_logs`: Security audit trail

### Vector Search
- **pgvector** for ReID embeddings (2048-dim ResNet or 185-dim CV features)
- **HNSW index** for fast similarity search (<10ms @ 1M vectors)

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=opensight_admin
POSTGRES_PASSWORD=changeme
POSTGRES_DB=opensight_db

# Security
API_SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
RATE_LIMIT_PER_MINUTE=60

# Video Processing
MAX_CAMERAS=16
DETECTION_CONFIDENCE=0.5
TRACKING_MAX_AGE=30
REID_THRESHOLD=0.6

# Storage
MEDIA_ROOT=/var/lib/opensight/media
CLIP_DURATION=10
THUMBNAIL_ENABLED=true

# Logging
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
```

See [.env.example](.env.example) for full list.

---

## 🚀 Production Deployment

### Systemd Service (Linux)
```ini
# /etc/systemd/system/opensight.service
[Unit]
Description=OpenSight Private Video Analytics
After=network.target docker.service

[Service]
Type=simple
User=opensight
WorkingDirectory=/opt/opensight/backend
Environment="PATH=/opt/opensight/venv/bin"
ExecStart=/opt/opensight/venv/bin/gunicorn app.main:app --workers 4 --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl;
    server_name opensight.example.com;

    ssl_certificate /etc/ssl/certs/opensight.crt;
    ssl_certificate_key /etc/ssl/private/opensight.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

---

## 🧪 Testing

```bash
# Run test suite
pytest backend/tests/ -v

# Coverage report
pytest backend/tests/ --cov=app --cov-report=html

# Security scan
bandit -r backend/app/
```

---

## 📈 Performance Benchmarks

| Hardware | Cameras | FPS/Stream | Latency | CPU | GPU |
|----------|---------|------------|---------|-----|-----|
| **Intel i7 + RTX 3060** | 16 | 25-30 | 80ms | 40% | 60% |
| **AMD Ryzen 9 + RTX 4090** | 64 | 25-30 | 45ms | 35% | 75% |
| **Intel i5 (CPU only)** | 8 | 15-20 | 150ms | 90% | N/A |

*Tested with 1080p@30fps streams, YOLOv8m, ByteTrack*

---

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

### Development Setup
```bash
# Install dev dependencies
pip install -r backend/requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Run linters
flake8 backend/app/
black backend/app/ --check
```

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
See [LICENSE](LICENSE) for details.

**Commercial licenses available** for organizations requiring proprietary deployment. Contact: enterprise@opensight.local

---

## 🙏 Acknowledgments

- **YOLOv8**: Ultralytics for object detection
- **ByteTrack**: ByteDance for multi-object tracking
- **pgvector**: PostgreSQL vector similarity search
- **FastAPI**: Sebastián Ramírez for the amazing framework
- **Streamlit**: Interactive dashboard framework

---

## 📞 Support

- **Documentation**: [Docs Portal](https://docs.opensight.local)
- **Issues**: [GitHub Issues](https://github.com/your-org/open-sight/issues)
- **Security Reports**: security@opensight.local (PGP key available)
- **Community**: [Discord Server](https://discord.gg/opensight)

---

**Built with ❤️ for privacy, security, and sovereignty.**  
*No clouds. No tracking. No compromises.*
