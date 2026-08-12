# Dependency provenance

This file is a starting inventory, not a substitute for checking the exact version/license before production use.

| Dependency | Role |
|---|---|
| Python | Runtime |
| FastAPI / Uvicorn | Local API |
| SQLAlchemy / Alembic | Database ORM and migrations |
| PostgreSQL / pgvector | Event and vector storage |
| OpenCV / FFmpeg | Video ingestion and media processing |
| Ultralytics | Object detection adapter |
| supervision / ByteTrack | Tracking adapter |
| Streamlit | Local dashboard |

Review upstream licenses and model terms for the versions you actually install.
