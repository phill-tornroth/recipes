.PHONY: help install install-dev format lint test test-cov clean run docker-build docker-up docker-down

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install

install-dev:  ## Install development dependencies
	poetry install --with dev

format:  ## Format code with black and isort
	poetry run black backend tests
	poetry run isort backend tests

lint:  ## Run linting tools
	poetry run flake8 backend tests
	poetry run mypy backend
	poetry run black --check backend tests
	poetry run isort --check-only backend tests

test:  ## Run tests
	poetry run pytest

test-cov:  ## Run tests with coverage
	poetry run pytest --cov=backend --cov-report=term-missing --cov-report=html

clean:  ## Clean up generated files
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run the application locally
	cd backend && poetry run uvicorn main:app --reload

docker-build:  ## Build Docker containers
	docker-compose build

docker-up:  ## Start Docker containers
	docker-compose up

docker-down:  ## Stop Docker containers
	docker-compose down

setup-pre-commit:  ## Setup pre-commit hooks
	poetry run pre-commit install

check-all: format lint test  ## Run all checks (format, lint, test)