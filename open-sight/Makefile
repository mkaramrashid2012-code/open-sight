.PHONY: up down api dashboard test lint migrate backup
up:
	docker compose up -d db
down:
	docker compose down
api:
	uvicorn app.main:app --app-dir backend --reload
dashboard:
	streamlit run frontend/app.py
test:
	PYTHONPATH=backend pytest -q
lint:
	ruff check backend frontend
migrate:
	cd backend && PYTHONPATH=. alembic -c alembic.ini upgrade head
backup:
	./scripts/backup.sh
