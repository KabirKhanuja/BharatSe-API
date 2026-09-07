.PHONY: install dev up down migrate revision keys train lint fmt test

install:
	python3.12 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

dev:
	.venv/bin/uvicorn app.main:app --reload --port 8000

up:
	docker compose up -d db

down:
	docker compose down

migrate:
	.venv/bin/alembic upgrade head

revision:
	.venv/bin/alembic revision --autogenerate -m "$(m)"

keys:
	.venv/bin/python scripts/generate_keys.py

train:
	.venv/bin/python -m app.services.pricing.train --csv data/seed/flipkart.csv

lint:
	.venv/bin/ruff check app tests

fmt:
	.venv/bin/ruff format app tests

test:
	.venv/bin/pytest -q
