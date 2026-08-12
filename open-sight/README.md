# OpenSight Private

A local/on-premises starter for authorized CCTV/IP-camera video analytics. The repository is deliberately modular so detection, tracking, storage, search, and UI can evolve independently.

## Current starter capabilities
- FastAPI backend with health and camera CRUD endpoints
- PostgreSQL + pgvector via Docker Compose
- SQLAlchemy models and Alembic-ready migrations
- RTSP/OpenCV camera capture abstraction
- Ultralytics detector adapter
- ByteTrack adapter through supervision
- Event/detection persistence models
- Basic event search API
- Streamlit private dashboard
- Retention and backup scripts
- Tests for core configuration/API behavior

## Start

1. Copy `.env.example` to `.env` and change secrets.
2. Start PostgreSQL: `docker compose up -d db`
3. Install Python dependencies: `python -m pip install -r backend/requirements.txt`
4. Run migrations: `alembic -c backend/alembic.ini upgrade head`
5. Start API: `uvicorn app.main:app --app-dir backend --reload`
6. Start dashboard: `streamlit run frontend/app.py`

The AI pipeline is intentionally staged: first get camera connectivity and persistence working, then enable inference/tracking. Use only cameras you are authorized to access.
