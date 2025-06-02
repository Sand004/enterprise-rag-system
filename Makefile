# Makefile for Enterprise RAG System

.PHONY: help dev-up dev-down test build deploy clean

# Default target
help:
	@echo "Enterprise RAG System - Available Commands:"
	@echo "  make dev-up        - Start development environment"
	@echo "  make dev-down      - Stop development environment"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e      - Run end-to-end tests"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make build         - Build all Docker images"
	@echo "  make build-prod    - Build production images"
	@echo "  make deploy-staging - Deploy to staging"
	@echo "  make deploy-prod   - Deploy to production"
	@echo "  make init-system   - Initialize system (first time setup)"
	@echo "  make clean         - Clean up temporary files"
	@echo "  make logs          - View application logs"
	@echo "  make shell         - Open shell in app container"
	@echo "  make format        - Format code with black/isort"
	@echo "  make lint          - Run linting checks"
	@echo "  make security-scan - Run security vulnerability scan"

# Development commands
dev-up:
	docker-compose -f docker/docker-compose.dev.yml up -d
	@echo "Development environment started! Access at http://localhost:8080"

dev-down:
	docker-compose -f docker/docker-compose.dev.yml down

dev-restart:
	$(MAKE) dev-down
	$(MAKE) dev-up

# Testing commands
test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/unit/ -v

test-integration:
	python -m pytest tests/integration/ -v

test-e2e:
	python -m pytest tests/e2e/ -v

test-coverage:
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Build commands
build:
	docker-compose -f docker/docker-compose.yml build

build-prod:
	docker-compose -f docker/docker-compose.prod.yml build

# Deployment commands
deploy-staging:
	./scripts/deploy.sh staging

deploy-prod:
	@echo "Production deployment requires confirmation."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	./scripts/deploy.sh production

# System initialization
init-system:
	./scripts/init_system.sh

# Utility commands
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/
	mypy src/
	pylint src/

security-scan:
	bandit -r src/
	safety check

logs:
	docker-compose -f docker/docker-compose.dev.yml logs -f

shell:
	docker-compose -f docker/docker-compose.dev.yml exec app bash

# Database commands
db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-reset:
	alembic downgrade base
	alembic upgrade head

# Monitoring commands
monitor-up:
	docker-compose -f docker/docker-compose.monitoring.yml up -d

monitor-down:
	docker-compose -f docker/docker-compose.monitoring.yml down