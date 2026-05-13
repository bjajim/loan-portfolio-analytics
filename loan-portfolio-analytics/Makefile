.PHONY: install dev test typecheck lint migrate seed up down

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v

typecheck:
	mypy app tests

lint:
	ruff check app tests
	ruff format --check app tests

format:
	ruff format app tests

migrate:
	alembic upgrade head

seed:
	python -m scripts.seed

up:
	docker-compose up --build

down:
	docker-compose down -v
