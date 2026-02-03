.PHONY: help install test lint format docker-build docker-up docker-down migrate backup

help:
	@echo "Data Platform - Make Commands"
	@echo ""
	@echo "install       - Install Python dependencies"
	@echo "test          - Run tests with coverage"
	@echo "lint          - Run linters (flake8, mypy)"
	@echo "format        - Format code with black and isort"
	@echo "docker-build  - Build Docker images"
	@echo "docker-up     - Start Docker services"
	@echo "docker-down   - Stop Docker services"
	@echo "migrate       - Run database migrations"
	@echo "migrate-create- Create new migration"
	@echo "backup        - Backup database"
	@echo "dev           - Run development server"

install:
	pip install -r backend/requirements.txt

test:
	pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term

lint:
	flake8 backend/
	mypy backend/

format:
	black backend/
	isort backend/

docker-build:
	cd docker && docker-compose build

docker-up:
	cd docker && docker-compose up -d

docker-down:
	cd docker && docker-compose down

docker-logs:
	cd docker && docker-compose logs -f

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MSG)"

backup:
	./scripts/backup.sh

dev:
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
