# OpenSight Private

OpenSight Private is a local, privacy-first video analytics platform skeleton designed for private, on-premises use.

It is built as a professional foundation for a system that can eventually ingest authorized camera streams, detect objects, track them over time, generate searchable events, and present results through a local dashboard.

This repository currently contains the professional core architecture and runnable local modules. It is designed to be extended with camera ingestion, AI detection, tracking persistence, search APIs, and a dashboard.

---

## What This Project Is

OpenSight Private is:

- a local-only video analytics foundation
- a modular Python project
- a professional tracking and event-analysis skeleton
- a privacy-focused system design
- a self-hosted platform intended for authorized cameras only

The current implementation includes:

- track lifecycle state machine
- trajectory smoothing
- track quality scoring
- explainable search query model
- evidence-style export packaging
- audit logging module
- case management module
- retention hold logic
- unit tests
- local demo runner
- PostgreSQL/pgvector schema for future persistence

This project is not a cloud service and does not send video, images, metadata, or telemetry to external servers.

---

## What This Project Is Not

This project is not:

- a complete commercial forensic video-search product
- a covert identification system
- a facial recognition identification platform by default
- a system that claims track IDs represent real-world identities
- a system that infers sensitive personal characteristics
- a system intended for unauthorized surveillance

Appearance similarity, if later implemented, is treated as an uncertain similarity score, not confirmed identity.

---

## Current Implementation Status

This repository is a runnable professional skeleton.

### Works now

You can currently run:

```bash
python run_demo.py
```

This demonstrates:

- track state transitions
- trajectory smoothing
- track quality scoring
- explainable search output
- evidence-style export generation

You can also run tests:

```bash
pytest
```

### Planned next stages

Future modules should be added in phases:

1. camera ingestion
2. object detection adapter
3. multi-object tracker adapter
4. PostgreSQL persistence
5. thumbnail and clip generation
6. search API
7. dashboard UI
8. retention worker
9. optional appearance embeddings
10. optional redaction tools

---

## Minimum Requirements to Run Locally

### Minimum requirements for the current skeleton

The current skeleton is lightweight and runs without cameras, GPU, Docker, or external services.

| Requirement | Minimum |
|---|---|
| Operating System | Windows 10/11, macOS 12+, or modern Linux |
| Python | 3.10 or newer |
| CPU | 2 cores |
| RAM | 4 GB |
| Disk Space | 1 GB free |
| GPU | Not required |
| Internet | Only required for initial `pip install` |
| Docker | Optional |
| Camera | Not required for demo/tests |

### Recommended requirements for future full video pipeline

When camera ingestion, detection, tracking, and clip generation are added, recommended hardware will be higher.

| Requirement | Recommended |
|---|---|
| CPU | 6+ cores |
| RAM | 16 GB |
| Disk | SSD with 50–200 GB free |
| GPU | Optional NVIDIA GPU with 6 GB+ VRAM |
| OS | Linux preferred for production, Windows/macOS supported for development |
| Database | PostgreSQL 16 with pgvector via Docker |
| Cameras | Authorized RTSP/IP cameras on local network |

The system should always support CPU-only operation, with GPU acceleration optional.

---

## Software Requirements

Required for the current skeleton:

- Python 3.10+
- pip
- virtualenv or Python `venv`

Optional:

- Docker
- Docker Compose
- PostgreSQL client tools
- Git

Python dependencies for the current skeleton:

```text
pytest
```

Future dependencies may include:

- FastAPI
- SQLAlchemy
- Alembic
- psycopg
- Pydantic
- OpenCV
- FFmpeg
- PyTorch
- Ultralytics YOLO or another approved detector
- pgvector-enabled PostgreSQL

All future dependencies must be reviewed for license, maintenance status, and provenance before being added.

---

## Project Structure

```text
opensight_private/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── run_demo.py
│
├── backend/
│   ├── tracking/
│   │   ├── state_machine.py
│   │   ├── trajectory.py
│   │   └── quality.py
│   │
│   ├── search/
│   │   └── explain.py
│   │
│   ├── security/
│   │   └── audit.py
│   │
│   ├── cases/
│   │   └── service.py
│   │
│   ├── retention/
│   │   └── service.py
│   │
│   └── evidence/
│       └── exporter.py
│
├── database/
│   └── schema.sql
│
└── tests/
    ├── test_state_machine.py
    ├── test_trajectory.py
    └── test_quality.py
```

---

## How to Build and Run Locally

### 1. Open the project folder

If the project was generated into a folder named `opensight_private`, open a terminal inside it:

```bash
cd opensight_private
```

---

### 2. Create a virtual environment

```bash
python -m venv .venv
```

---

### 3. Activate the virtual environment

#### Windows Command Prompt

```cmd
.venv\Scripts\activate
```

#### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you may need to allow local scripts:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Linux/macOS

```bash
source .venv/bin/activate
```

---

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

For the current skeleton, this installs only `pytest`.

---

### 5. Run the demo

```bash
python run_demo.py
```

This will create local output folders:

```text
output/
exports/
```

The demo writes files such as:

```text
output/track_states.json
output/trajectory.json
output/quality.json
output/search_explanation.json
exports/demo-case-.../
```

---

### 6. Run tests

```bash
pytest
```

Expected result:

```text
3 passed
```

If more tests are added later, the count may increase.

---

## Optional Docker Database Setup

The current demo does not require a database.

However, the project includes a PostgreSQL schema for future persistence.

To start PostgreSQL with pgvector using Docker:

```bash
docker compose up -d db
```

The database schema is automatically mounted into the container. If the database volume has already been initialized before adding the schema, apply it manually:

```bash
docker compose exec -T db psql -U opensight -d opensight -f /docker-entrypoint-initdb.d/schema.sql
```

Default database credentials in `docker-compose.yml` are:

```text
Database: opensight
User: opensight
Password: change_me
```

Change these before serious use.

---

## Optional Docker Run

You can also run the demo inside a container:

```bash
docker build -t opensight-private .
docker run --rm opensight-private
```

This runs:

```bash
python run_demo.py
```

inside the container.

---

## Environment Configuration

Copy the example environment file:

### Linux/macOS

```bash
cp .env.example .env
```

### Windows

```cmd
copy .env.example .env
```

Then edit `.env` and change secrets:

```env
SECRET_KEY=CHANGE_ME
ADMIN_PASSWORD=CHANGE_ME
POSTGRES_PASSWORD=CHANGE_ME
```

Never commit real credentials to source control.

The `.gitignore` file excludes:

```text
.env
output/
exports/
media/
.venv/
```

---

## What the Demo Does

The demo runner, `run_demo.py`, demonstrates the professional core modules without requiring cameras or a database.

It performs the following:

### 1. Track lifecycle simulation

It simulates a sequence of matched and missed detection frames.

The tracking state machine transitions through states such as:

```text
tentative
active
occluded
recovered
```

Output:

```text
output/track_states.json
```

---

### 2. Trajectory smoothing

It creates sample trajectory points, including an unrealistic jump, and smooths the path.

Output:

```text
output/trajectory.json
```

---

### 3. Track quality scoring

It computes a quality score from:

- confidence
- continuity
- smoothness
- occlusion/loss ratio
- embedding quality placeholder

Output:

```text
output/quality.json
```

---

### 4. Explainable search

It builds a structured search query and generates a human-readable explanation.

Example filters:

```text
object class = person
color = red
minimum confidence = 0.50
minimum quality = 0.65
```

Output:

```text
output/search_explanation.json
```

---

### 5. Evidence export

It creates a simple evidence-style export package containing:

```text
manifest.json
checksums.sha256
items/
```

Output folder:

```text
exports/demo-case-.../
```

---

## Testing

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Current tests cover:

- track state machine transitions
- trajectory smoothing behavior
- track quality scoring behavior

---

## Privacy Defaults

This project is designed with privacy controls from the start.

Default posture:

```text
Face processing: disabled
Face embedding: disabled
Face matching: disabled
License plate recognition: disabled
Automatic face blur: disabled by default but planned as optional
Cloud processing: disabled
External telemetry: disabled
Continuous video retention: discouraged by default
Event-based retention: preferred
```

If face or license plate functionality is added later, it must be:

- optional
- disabled by default
- explicitly configured
- audited
- clearly separated from detection and tracking
- not used for covert identification

---

## Security Guidelines

For local private use, follow these rules:

1. Do not expose camera streams publicly.
2. Do not hard-code passwords.
3. Keep secrets in `.env`.
4. Use strong passwords.
5. Change default database credentials.
6. Restrict access to the machine and local network.
7. Use HTTPS/TLS if exposing the dashboard on a LAN.
8. Keep backups of the database and important exports.
9. Regularly review audit logs.
10. Test restore procedures, not only backups.

---

## Provenance and Dependency Policy

This project is intended to use only dependencies whose origin, license, and maintenance status can be confidently verified.

Before adding any new dependency, record:

```text
name
version
official source
organization
license
reason for inclusion
verification date
```

Do not add dependencies if:

- the license is unclear
- the origin cannot be verified
- the dependency is abandoned
- the dependency requires external cloud processing
- the dependency introduces telemetry by default
- the dependency violates the project provenance requirements

For AI models, also record:

```text
model name
model version
weights source
weights license
supported classes
intended use
limitations
```

---

## Troubleshooting

### `python` is not recognized

Install Python 3.10 or newer from:

```text
https://www.python.org/
```

During installation on Windows, enable:

```text
Add Python to PATH
```

---

### `pytest` is not recognized

Make sure the virtual environment is activated, then run:

```bash
pip install -r requirements.txt
```

Then:

```bash
pytest
```

---

### `docker compose` is not recognized

Install Docker Desktop or Docker Engine with Compose support.

For Windows/macOS, Docker Desktop is usually easiest.

For Linux, install Docker Engine and the Docker Compose plugin.

---

### Database schema does not apply automatically

Docker PostgreSQL initialization scripts usually run only when the database volume is first created.

If the volume already exists, either remove the volume and recreate it, or apply the schema manually.

Warning: removing the volume deletes database data.

```bash
docker compose down -v
docker compose up -d db
```

Or apply manually:

```bash
docker compose exec -T db psql -U opensight -d opensight -f /docker-entrypoint-initdb.d/schema.sql
```

---

### Demo export fails because folder already exists

The export module refuses to overwrite an existing export folder.

Either delete the previous export folder or run the demo again after moving it.

Export folders are created under:

```text
exports/
```

---

## Roadmap

### Phase 1 — Current

Completed in this skeleton:

- project structure
- tracking state machine
- trajectory smoothing
- quality scoring
- explainable search model
- evidence export
- tests
- demo runner

### Phase 2 — Persistence

Next:

- connect to PostgreSQL
- save tracks
- save track state changes
- save audit logs
- save cases
- save search jobs

### Phase 3 — Video Pipeline

Next:

- RTSP camera ingestion
- frame sampling
- detector adapter
- tracker adapter
- detection persistence
- thumbnail generation

### Phase 4 — Search and Dashboard

Next:

- FastAPI search API
- structured search endpoint
- dashboard UI
- timeline view
- track detail view
- case management UI

### Phase 5 — Advanced Analytics

Later:

- zones
- line crossing
- direction estimation
- appearance embeddings
- cross-camera similarity
- redaction tools
- retention automation

---

## Acceptance Criteria for a Professional Local Build

Before considering this project production-ready for private use, verify:

- [ ] Demo runs successfully.
- [ ] Tests pass.
- [ ] No external network calls are made during demo execution.
- [ ] Secrets are not hardcoded.
- [ ] Database migrations or schema can be applied cleanly.
- [ ] Audit logging works.
- [ ] Retention holds prevent deletion of case-linked evidence.
- [ ] Export packages contain checksums and manifests.
- [ ] Camera streams are not publicly exposed.
- [ ] Face/plate features remain disabled by default.
- [ ] Dependency provenance is documented.
- [ ] Backup and restore procedures are tested.

---

## Summary

OpenSight Private is a local, private, professional-grade foundation for video analytics.

It is designed to be:

- modular
- testable
- auditable
- privacy-preserving
- locally controlled
- extendable
- free from forced cloud dependencies

The current version runs immediately on a normal PC and provides the core professional logic needed before adding cameras, AI models, dashboards, and full persistence.
It is still in it's development phase and is a prototype we would be contributing to it to improve the skeleton and soon make it a full professional software
Fo developers both the skeleton and the prototype is published in the repo both in different folders for better arrangment 

                                  -------------------DISCLAIMER----------------------
This is for educational and safe keeping surveillance tool and is not meant for inappropriate or bad purposes and it would be hoped that it would be used for personal legitimate use                                  
