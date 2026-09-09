.PHONY: help up down restart ps logs test lint format ingest dbt-run dbt-test train evaluate retrain drift score serve dashboard docker-build docker-run clean

help:
	@echo "Available commands:"
	@echo "  make up          - Start all docker services (Postgres, MinIO, MLflow, Airflow)"
	@echo "  make down        - Stop all docker services"
	@echo "  make ps          - Show status of services"
	@echo "  make logs        - Follow logs from all docker containers"
	@echo "  make ingest      - Download dataset and ingest into raw postgres"
	@echo "  make dbt-run     - Run dbt models (staging -> intermediate -> marts)"
	@echo "  make dbt-test    - Run dbt data tests"
	@echo "  make train       - Train churn models and log runs to MLflow"
	@echo "  make evaluate    - Compare candidate model against production and promote"
	@echo "  make retrain     - Run end-to-end training and promotion pipeline"
	@echo "  make score       - Run daily batch scoring on active customers"
	@echo "  make serve       - Start FastAPI real-time model serving endpoint"
	@echo "  make dashboard   - Launch Streamlit interactive retention dashboard"
	@echo "  make docker-build- Build standalone FastAPI serving Docker container"
	@echo "  make docker-run  - Run standalone FastAPI serving container on port 8000"
	@echo "  make drift       - Generate Evidently data drift report"
	@echo "  make test        - Run unit tests with pytest"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Format code with black and isort"
	@echo "  make clean       - Remove cache and compiled files"

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

ps:
	docker compose ps

logs:
	docker compose logs -f

ingest:
	python -m src.data.ingest

dbt-run:
	cd dbt && dbt run --profiles-dir .

dbt-test:
	cd dbt && dbt test --profiles-dir .

train:
	python -m src.training.train

evaluate:
	python -m src.training.evaluate

retrain:
	python -m src.training.train
	python -m src.training.evaluate

score:
	python -m src.scoring.score

serve:
	uvicorn src.serving.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	streamlit run streamlit_app/app.py

docker-build:
	docker build -t churn-serving:latest .

docker-run:
	docker run -d -p 8000:8000 --name churn_serving churn-serving:latest

drift:
	python -m src.monitoring.drift

test:
	pytest tests/unit/ -v --cov=src

lint:
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
