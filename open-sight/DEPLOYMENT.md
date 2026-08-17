# OpenSight Private - Enterprise Deployment Guide

## Quick Start (Development)

```bash
# 1. Start database
docker compose up -d db

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run migrations
alembic upgrade head

# 5. Start API server
uvicorn app.main:app --reload

# 6. Start frontend (optional)
cd ../frontend
streamlit run app.py
```

## Production Deployment

### Prerequisites

- Ubuntu 22.04+ or RHEL 8+
- Docker 24+ and Docker Compose 2.20+
- PostgreSQL client tools
- Python 3.10+
- 8GB+ RAM (16GB recommended for multiple cameras)
- GPU optional (NVIDIA with CUDA for accelerated inference)

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip \
    libopencv-dev ffmpeg git curl

# Create application user
sudo useradd -r -m -s /bin/bash opensight
sudo mkdir -p /opt/opensight
sudo chown opensight:opensight /opt/opensight
```

### Step 2: Security Configuration

```bash
# Generate secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

# Generate database password
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create production .env file
cat > /opt/opensight/.env << ENVEOF
SECRET_KEY=${SECRET_KEY}
ENVIRONMENT=production
ALLOW_ANONYMOUS=false
DEBUG=false

POSTGRES_USER=opensight_prod
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=opensight_prod
DATABASE_URL=postgresql+psycopg://opensight_prod:${DB_PASSWORD}@localhost:5432/opensight_prod

HOST=127.0.0.1
PORT=8000
CORS_ORIGINS=["https://your-domain.com"]

LOG_LEVEL=WARNING
ENABLE_AUDIT_LOGGING=true

MAX_CONCURRENT_CAMERAS=16
ENVEOF

# Secure the file
chmod 600 /opt/opensight/.env
chown opensight:opensight /opt/opensight/.env
```

### Step 3: Database Setup

```bash
# Option A: Using Docker (recommended)
cd /opt/opensight
docker compose up -d db

# Wait for database to be ready
sleep 10

# Option B: Native PostgreSQL installation
sudo apt install -y postgresql-16 postgresql-contrib
sudo -u postgres psql << SQLEOF
CREATE DATABASE opensight_prod;
CREATE USER opensight_prod WITH PASSWORD '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE opensight_prod TO opensight_prod;
\\c opensight_prod
CREATE EXTENSION IF NOT EXISTS vector;
SQLEOF
```

### Step 4: Application Installation

```bash
# Clone repository
cd /opt/opensight
git clone https://github.com/your-org/open-sight-private.git .
git checkout v1.0.0  # Use specific version tag

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
export $(cat ../.env | xargs)
alembic upgrade head

# Test installation
python -c "from app.core.config import settings; print('Config OK')"
```

### Step 5: Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/opensight.service > SVCEOF
[Unit]
Description=OpenSight Private Video Analytics
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=opensight
Group=opensight
WorkingDirectory=/opt/opensight/backend
EnvironmentFile=/opt/opensight/.env
ExecStart=/opt/opensight/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SVCEOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable opensight
sudo systemctl start opensight

# Check status
sudo systemctl status opensight
```

### Step 6: Reverse Proxy (nginx)

```bash
# Install nginx
sudo apt install -y nginx

# Create nginx configuration
sudo tee /etc/nginx/sites-available/opensight > NGINXEOF
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }

    # Media files
    location /media/ {
        alias /opt/opensight/data/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Frontend (Streamlit)
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://\$server_name\$request_uri;
}
NGINXEOF

# Enable site
sudo ln -s /etc/nginx/sites-available/opensight /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Monitoring & Logging

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/opensight > ROTATEEOF
/opt/opensight/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 opensight opensight
    postrotate
        systemctl reload opensight
    endscript
}
ROTATEEOF

# Optional: Install Prometheus exporter
pip install prometheus-fastapi-instrumentator

# Add to main.py after app creation:
# from prometheus_fastapi_instrumentator import Instrumentator
# Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

### Step 8: Backup Strategy

```bash
# Create backup script
sudo tee /opt/opensight/scripts/backup.sh << 'BACKUPEOF'
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/opensight"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p ${BACKUP_DIR}

# Database backup
pg_dump -h localhost -U opensight_prod opensight_prod | \
    gzip > ${BACKUP_DIR}/db_${DATE}.sql.gz

# Configuration backup
tar czf ${BACKUP_DIR}/config_${DATE}.tar.gz \
    /opt/opensight/.env \
    /etc/nginx/sites-available/opensight \
    /etc/systemd/system/opensight.service

# Delete old backups
find ${BACKUP_DIR} -name "*.gz" -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: ${DATE}"
BACKUPEOF

chmod +x /opt/opensight/scripts/backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/opensight/scripts/backup.sh >> /var/log/opensight-backup.log 2>&1" | \
    sudo crontab -
```

## High Availability Setup

### Multi-Node Architecture

```
                    ┌─────────────┐
                    │   Load      │
                    │  Balancer   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
   │  Node 1   │     │  Node 2   │     │  Node 3   │
   │ OpenSight │     │ OpenSight │     │ OpenSight │
   └─────┬─────┘     └─────┬─────┘     └─────┬─────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │   Primary   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │  Replica    │
                    └─────────────┘
```

### Shared Storage (NFS)

```bash
# On NFS server
sudo apt install -y nfs-kernel-server
sudo mkdir -p /srv/opensight-media
sudo echo "/srv/opensight-media *(rw,sync,no_subtree_check)" >> /etc/exports
sudo exportfs -a

# On each application node
sudo apt install -y nfs-common
sudo mount -t nfs nfs-server:/srv/opensight-media /opt/opensight/data/media
```

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials
psql -h localhost -U opensight_prod -d opensight_prod

# Check pgvector extension
psql -d opensight_prod -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

**Camera stream failures:**
```bash
# Test RTSP stream with ffplay
ffplay rtsp://camera-ip/stream

# Check firewall rules
sudo ufw status
sudo ufw allow from 192.168.1.0/24 to any port 554
```

**High CPU usage:**
```bash
# Reduce concurrent cameras
# Edit .env: MAX_CONCURRENT_CAMERAS=8

# Lower processing FPS
# Edit .env: PROCESSING_FPS_TARGET=3.0

# Enable GPU acceleration
# Edit .env: MODEL_DEVICE=cuda
```

## Performance Tuning

### GPU Acceleration (NVIDIA)

```bash
# Install NVIDIA drivers and container toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Update docker-compose.yml to use GPU
# Add to db service:
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: 1
#           capabilities: [gpu]

# Set in .env
MODEL_DEVICE=cuda
```

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_detections_class_time 
ON detections(object_class, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_detections_track_camera 
ON detections(track_id, camera_id) WHERE track_id IS NOT NULL;

-- Vacuum and analyze
VACUUM ANALYZE detections;
VACUUM ANALYZE cameras;
```

## Support

For enterprise support, contact:
- Documentation: https://docs.opensight-private.local
- Security advisories: security@opensight-private.local
- Community forum: https://community.opensight-private.local
