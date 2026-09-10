# 🔄 End-to-End Customer Churn Prediction & Retention MLOps Pipeline

[![CI Checks](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions)
[![Retrain & Promotion](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions/workflows/train-and-promote.yml/badge.svg)](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions)
[![Publish Serving Container](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions/workflows/deploy.yml/badge.svg)](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions)
[![Terraform CI](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions/workflows/terraform.yml/badge.svg)](https://github.com/Alokkr00/Customer-Churn-Pipeline/actions)
[![Docker Image: ghcr.io](https://img.shields.io/badge/GHCR-Serving%20Container-2496ED?logo=docker&logoColor=white)](https://github.com/Alokkr00/Customer-Churn-Pipeline/pkgs/container/customer-churn-pipeline%2Fserving)
[![IaC: Terraform](https://img.shields.io/badge/IaC-Terraform%201.7+-844FBA.svg?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Cloud: AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20RDS%20%7C%20S3-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Python 3.11](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![dbt](https://img.shields.io/badge/dbt--core-1.7-FF694B.svg?logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![MLflow](https://img.shields.io/badge/MLflow-2.10-0194E2.svg?logo=mlflow&logoColor=white)](https://mlflow.org/)
[![Apache Airflow](https://img.shields.io/badge/Airflow-2.8-017CEE.svg?logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-grade, end-to-end Machine Learning Operations (**MLOps**) and Data Engineering system designed to predict customer churn, explain individual risk drivers, and automate proactive retention campaigns for recurring subscription and SaaS businesses.

---

## 📑 Table of Contents
- [Business Problem & ROI](#business-problem--roi)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Layout](#project-layout)
- [Quickstart Guide](#quickstart-guide)
- [REST API Reference (FastAPI)](#rest-api-reference-fastapi)
- [Interactive Retention Hub (Streamlit)](#interactive-retention-hub-streamlit)
- [Model Governance & Promotion Gate](#model-governance--promotion-gate)
- [Continuous ML & Container Deployment (Phase 4)](#continuous-ml--container-deployment-phase-4)
- [Cloud Infrastructure & Terraform (Phase 5)](#cloud-infrastructure--terraform-phase-5)
- [Testing & Code Quality](#testing--code-quality)
- [Roadmap](#roadmap)

---

## 💼 Business Problem & ROI

### The Challenge
In recurring subscription businesses (telecoms, SaaS, streaming services), customer churn directly erodes customer lifetime value (LTV). Acquiring a new customer costs **5–7× more** than retaining an existing one. Reactive retention strategies (calling customers *after* they cancel) fail because churn signals develop weeks in advance.

### The Solution
An automated, closed-loop MLOps pipeline that:
1. **Identifies Vulnerability Early**: Scans customer activity and contract patterns daily to score churn probability.
2. **Diagnoses Why**: Isolates top individual risk drivers (e.g. month-to-month contracts, missing tech support, high recurring charges) for transparent, explainable AI.
3. **Automates Actionable Interventions**: Maps risk factors directly to prioritized retention campaigns (e.g. 15% discount for 12-month lock-in, complimentary tech support).
4. **Protects Production Quality**: Enforces strict automated promotion gates ($\Delta\text{AUC} \ge +0.01$ and Population Stability Index $\le 0.10$) before any model reaches serving.

### Business & ML Success Metrics
- **Target ROC-AUC**: $\ge 0.84$ on unseen holdout sets.
- **Precision@20%**: Measures the churn concentration in the top quintile highest-risk customers flagged for proactive outreach.
- **Revenue at Risk Protected**: Identifies high-risk customer accounts to prioritize high-touch retention campaigns.
- **Prediction Latency**: Sub-30ms real-time inference via FastAPI.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion & Transformation ["Data Layer (PostgreSQL & dbt)"]
        A[IBM Telco Raw Dataset] -->|ingest.py| B[(raw.telco_customers)]
        B -->|dbt run| C[stg_customers\nCleaned & Typecast]
        C -->|dbt run| D[int_customer_features\nTenure Cohorts & Service Bundles]
        D -->|dbt run| E[(marts.mart_churn_features\nProduction Feature Mart)]
    end

    subgraph Training & Governance ["ML & Experiment Tracking (MLflow & MinIO)"]
        E --> F[Feature Engineering Pipeline\nColumnTransformer & OneHotEncoder]
        F --> G[Baseline: Logistic Regression]
        F --> H[Champion: LightGBM Classifier]
        G -->|Metrics & Artifacts| I[MLflow Tracking Server]
        H -->|Metrics & Artifacts| I
        I --> J{evaluate.py\nPromotion Gate}
        J -->|Candidate AUC > Prod + 0.01\n& PSI Drift < 0.10| K[(Production Model Cache\nMinIO / models/)]
        J -->|Failed Gate| L[Keep Current Champion]
    end

    subgraph Scoring & Orchestration ["Batch Scoring (Apache Airflow 2.8)"]
        K --> M[Airflow DAG: daily_scoring]
        M --> N[score.py Batch Engine]
        N --> O[(scoring.churn_scores)]
        N --> P[reports/high_risk_customers.csv]
    end

    subgraph Serving & UI ["Serving Layer (FastAPI & Streamlit)"]
        K --> Q[FastAPI Serving Service\n/predict & /high-risk]
        O --> R[Streamlit Retention Hub\nDashboard & What-If Simulator]
        P --> R
    end

    subgraph Monitoring ["Monitoring (Evidently AI)"]
        E --> S[drift.py\nKS-Tests & PSI Drift Report]
        S --> T[reports/data_drift_report.html]
    end
```

---

## 🌟 Key Features

* **Dynamic Platform-Agnostic Directory Resolution**: Custom path engine (`src/utils/paths.py`) that auto-discovers repository root and works seamlessly across Windows, macOS, Linux, Docker, and Airflow worker environments.
* **Modular dbt Models**: Staging, intermediate, and marts layers with unit schema constraints (`unique`, `not_null`, `accepted_values`).
* **Automated Production Quality Gate**: Replaces manual deployments with code-enforced promotion criteria based on both performance gain and population drift.
* **Explainable Risk Diagnostics**: Provides human-readable churn risk reasons per customer for transparent customer support action.
* **What-If Retention Strategy Simulator**: Interactive Streamlit simulator allowing retention teams to test how plan adjustments (e.g. extending contract duration or bundling tech support) lower a customer's churn risk.
* **Full CI/CD Pipeline**: GitHub Actions running code formatting (Ruff/Black), unit test verification, and dbt compile checks on every pull request.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Local Infrastructure** | Docker Compose | 1-command spinup of PostgreSQL 15, MinIO, MLflow, and Apache Airflow |
| **Data Storage** | PostgreSQL 15 | Relational data warehouse, raw storage, feature mart, and churn scores |
| **Data Transformation** | dbt-core + dbt-postgres | SQL transformations, schema testing, and lineage tracking |
| **ML Modeling** | LightGBM, Scikit-learn | Gradient boosted trees and benchmark linear models |
| **Experiment Tracking** | MLflow + MinIO | Run parameters, metrics, artifact logging, and model registry |
| **Orchestration** | Apache Airflow 2.8 | Scheduled daily scoring pipeline and risk volume alerts |
| **Real-Time Serving** | FastAPI + Uvicorn | High-performance REST endpoints with Pydantic validation |
| **Retention UI** | Streamlit | Executive KPI dashboard, risk cohort table, and retention simulator |
| **Data Quality & Drift** | Evidently AI + Scipy | Kolmogorov-Smirnov tests and Population Stability Index (PSI) |
| **CI / CD** | GitHub Actions | Automated pull request testing, linting, and dbt validation |

---

## 📂 Project Layout

```text
customer-churn-pipeline/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # PR & push validation (ruff, black, pytest, dbt parse)
│       ├── train-and-promote.yml  # Automated retraining & model promotion quality gate
│       ├── deploy.yml             # Build & publish serving container to GHCR
│       └── terraform.yml          # Terraform format and validate CI
├── infra/                         # Production Terraform Infrastructure-as-Code (AWS)
│   ├── modules/
│   │   ├── networking/            # VPC, public/private subnets, NAT GW, security groups
│   │   ├── database/              # RDS PostgreSQL 15, Secrets Manager credentials
│   │   ├── storage/               # S3 MLflow artifact bucket, AES256 encryption
│   │   └── serving/               # ECS Fargate, ALB, Target Groups, Auto Scaling
│   ├── environments/
│   │   ├── dev/                   # Dev environment configuration & tfvars
│   │   └── prod/                  # Prod environment (multi-AZ, high availability)
│   └── README.md                  # Cloud architecture & deployment guide
├── airflow/
│   └── dags/
│       └── daily_scoring.py       # Daily batch scoring + Slack spike webhook alert
├── dbt/
│   ├── models/
│   │   ├── staging/               # stg_customers.sql + schema.yml
│   │   ├── intermediate/          # int_customer_features.sql + schema.yml
│   │   └── marts/                 # mart_churn_features.sql + schema.yml
│   ├── dbt_project.yml
│   └── profiles.yml
├── docs/
│   └── demo_script.md             # 3-minute portfolio presentation walkthrough
├── scripts/
│   └── init_db.sql                # PostgreSQL init for raw, marts, and scoring schemas
├── src/
│   ├── data/
│   │   ├── ingest.py              # Raw ingestion to raw.telco_customers
│   │   └── preprocess.py          # Data cleaning and staging
│   ├── features/
│   │   └── feature_engineering.py # Scikit-learn ColumnTransformer pipeline
│   ├── training/
│   │   ├── train.py               # LogReg + LightGBM training with MLflow tracking
│   │   └── evaluate.py            # Automated promotion gate (AUC delta + drift)
│   ├── scoring/
│   │   └── score.py               # Batch scoring engine & top driver diagnostics
│   ├── serving/
│   │   ├── main.py                # FastAPI real-time REST API
│   │   └── schemas.py             # Pydantic v2 schemas
│   ├── monitoring/
│   │   ├── alerts.py              # Anomaly detection & Slack Block Kit notifications
│   │   └── drift.py               # Evidently & statistical drift monitoring
│   └── utils/
│       └── paths.py               # Dynamic platform-agnostic directory resolution
├── streamlit_app/
│   └── app.py                     # Streamlit Retention Dashboard & Simulator
├── tests/
│   └── unit/                      # 24 unit tests (data, features, models, alerts, API)
├── Dockerfile                     # Multi-stage production container build for FastAPI
├── .dockerignore                  # Container image build exclusion rules
├── docker-compose.yml             # Postgres, MinIO, MLflow, Airflow local stack
├── Makefile                       # Developer shortcuts (train, test, serve, docker, tf)
├── requirements.txt               # Pinned dependencies
├── pyproject.toml                 # Package definition & tool configs
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Docker Desktop installed and running
- Git

### 1. Clone & Setup Environment
```bash
git clone https://github.com/Alokkr00/Customer-Churn-Pipeline.git
cd Customer-Churn-Pipeline

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Start Local Infrastructure
```bash
make up
# Or: docker compose up -d
```
Access infrastructure dashboards:
- **MLflow UI**: [http://localhost:5000](http://localhost:5000)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
- **Airflow Webserver**: [http://localhost:8080](http://localhost:8080) (`admin` / `admin`)
- **PostgreSQL**: `localhost:5432` (`churn_db`, user: `churn_user`)

### 3. Ingest Data & Run dbt Transformations
```bash
make ingest     # Ingest raw dataset into raw.telco_customers
make dbt-run    # Transform data through staging -> intermediate -> marts
make dbt-test   # Run dbt data tests
```

### 4. Train Models & Promote to Production
```bash
make train      # Train Logistic Regression & LightGBM; log to MLflow
make evaluate   # Evaluate promotion gate (ΔAUC >= 0.01 & PSI <= 0.10)
```

### 5. Run Batch Scoring
```bash
make score      # Score customers, write to DB, and export high_risk_customers.csv
```

### 6. Start FastAPI Serving API
```bash
make serve
# Swagger documentation available at: http://localhost:8000/docs
```

### 7. Launch Streamlit Retention Hub
```bash
make dashboard
# Dashboard available at: http://localhost:8501
```

---

## 📡 REST API Reference (FastAPI)

When running `make serve`, the API documentation is interactively accessible at `http://localhost:8000/docs`.

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health and model readiness probe |
| `GET` | `/model-info` | Active production model metadata, parameters, and version |
| `POST` | `/predict` | Real-time churn prediction for a single customer with risk drivers |
| `POST` | `/predict-batch` | High-throughput batch prediction for a customer list |
| `GET` | `/high-risk` | Query high-risk customer cohort (`?threshold=0.65&limit=100`) |

### Example: Single Customer Prediction
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_id": "CUST-9821-HIGH",
       "tenure_months": 3,
       "contract_type": "Month-to-month",
       "internet_service": "Fiber optic",
       "online_security": "No",
       "tech_support": "No",
       "payment_method": "Electronic check",
       "monthly_charges": 89.20
     }'
```

**Response**:
```json
{
  "customer_id": "CUST-9821-HIGH",
  "churn_probability": 0.8142,
  "churn_prediction": 1,
  "risk_tier": "High",
  "top_risk_drivers": [
    "Month-to-month contract (low lock-in)",
    "New customer in high-vulnerability first year",
    "Electronic check payment (higher historic default & churn)"
  ],
  "recommended_retention_action": "Offer 15% discount for 1-year contract lock-in.",
  "model_version": "production_v1",
  "latency_ms": 14.82
}
```

---

## 🎯 Interactive Retention Hub (Streamlit)

Run `make dashboard` to launch the interactive retention portal:
1. **Executive Overview**: Real-time KPI summary tracking total accounts, high-risk churn rate, and monthly/annual revenue at risk.
2. **High-Risk Retention Workspace**: Searchable, filterable list of customers sorted by churn probability with 1-click CSV export for email or outreach campaign tooling.
3. **"What-If" Customer Simulator**: Real-time experimentation sandbox allowing retention specialists to test adjustments to customer contract duration, billing methods, and add-on services to see predicted churn risk drop live.
4. **Model Health & Drift**: Displays active model hyperparameters and checks for data drift via Kolmogorov-Smirnov statistical tests.

---

## 🛡️ Model Governance & Promotion Gate

To prevent degraded or drifting models from reaching production, `src/training/evaluate.py` enforces a two-factor quality gate:

$$\Delta\text{AUC} = \text{AUC}_{\text{candidate}} - \text{AUC}_{\text{production}} \ge 0.01$$

$$\text{PSI}(\text{Dist}_{\text{production}}, \text{Dist}_{\text{candidate}}) \le 0.10$$

```python
if (candidate_auc >= production_auc + 0.01) and (drift_psi_score <= 0.10):
    # Promote to Production in MLflow Model Registry and cache locally
    promote_model(candidate)
else:
    # Reject candidate and preserve active champion
    retain_production_model()
```

## 🚢 Continuous ML & Container Deployment (Phase 4)

### 1. Automated Weekly Retraining & Promotion Pipeline
GitHub Actions workflow [`.github/workflows/train-and-promote.yml`](.github/workflows/train-and-promote.yml) triggers automatically on a schedule (every Monday at 02:00 AM UTC) or on-demand via `workflow_dispatch`:
1. Checks out repository and provisions Python 3.11 with cached pip wheels.
2. Ingests the latest customer dataset and trains both Logistic Regression and LightGBM classifiers.
3. Automatically executes the two-factor promotion gate ($\Delta\text{AUC} \ge 0.01$ and $\text{PSI} \le 0.10$).
4. Generates an interactive Markdown summary directly in `$GITHUB_STEP_SUMMARY`.
5. Archives and persists the production model binaries (`models/`) as a 30-day workflow artifact.

### 2. Container Image Publishing to GHCR
Workflow [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) automatically triggers upon successful model promotion:
- Uses a multi-stage production [`Dockerfile`](Dockerfile) (`python:3.11-slim`) with non-root security principles (`appuser`).
- Builds and signs Docker images tagged with `latest`, commit SHA (`sha-<short-hash>`), and build date.
- Pushes directly to the GitHub Container Registry (**GHCR**):
  ```bash
  # Pull production image
  docker pull ghcr.io/alokkr00/customer-churn-pipeline/serving:latest

  # Run standalone prediction service locally
  docker run -d -p 8000:8000 --name churn-api ghcr.io/alokkr00/customer-churn-pipeline/serving:latest
  ```

### 3. Anomaly Alerts via Slack Block Kit & Webhooks
The daily batch scoring pipeline in [`airflow/dags/daily_scoring.py`](airflow/dags/daily_scoring.py) continuously monitors churn vulnerability distribution:
- If the high-risk customer ratio exceeds the business threshold (configurable via Airflow Variable `HIGH_RISK_THRESHOLD_PCT`, default `35.0%`), it dispatches an urgent Slack Block Kit notification containing:
  - 🚨 High-risk volume and percentage metrics
  - Churn SLA breach warning
  - Direct 1-click CTA button opening the **Streamlit Retention Dashboard**
- Gracefully falls back if webhooks are unconfigured, ensuring zero pipeline interruption.

---

## ☁️ Cloud Infrastructure & Terraform (Phase 5)

Complete Infrastructure-as-Code (IaC) configuration located under [`infra/`](infra/) enables 1-command deployment of the serving architecture to **Amazon Web Services (AWS)**.

### Architecture Overview
```text
Internet
   │
   ▼
[ Application Load Balancer (ALB) ] (Public Subnets: 10.0.1.0/24, 10.0.2.0/24)
   │
   │  Port 8000
   ▼
[ ECS Fargate Service ] (Private Subnets: 10.0.10.0/24, 10.0.20.0/24)
   │  Image: ghcr.io/alokkr00/customer-churn-pipeline/serving:latest
   │  Target Tracking Auto-scaling (CPU > 70%)
   │
   ├──► [ Amazon S3 ] (MLflow Model Artifacts with AES256 Encryption)
   └──► [ Amazon RDS PostgreSQL 15 ] (Private Subnets, Port 5432)
```

### Modular Structure
* **[`infra/modules/networking`](infra/modules/networking/)**: Custom VPC (`10.0.0.0/16`), 2 public subnets, 2 private subnets, Internet Gateway, NAT Gateway, route tables, and granular Security Groups.
* **[`infra/modules/storage`](infra/modules/storage/)**: Versioned, AES256-encrypted S3 bucket for MLflow models with strict public access blocks.
* **[`infra/modules/database`](infra/modules/database/)**: RDS PostgreSQL 15 instance with automatic DB subnet grouping and credentials stored in AWS Secrets Manager.
* **[`infra/modules/serving`](infra/modules/serving/)**: ECS Cluster, CloudWatch log groups, IAM roles, Fargate Task Definition, ALB with `/health` checks, and CPU target tracking auto-scaling.

### Multi-Environment Strategy & Cost Breakdown

| Environment | RDS Instance | Multi-AZ | Fargate Task Size | Task Replicas | Est. Monthly Cost |
|---|---|---|---|---|---|
| **Dev** | `db.t3.micro` | Disabled | 0.25 vCPU / 512 MB | 1 (min 1, max 2) | ~$18 - $28 |
| **Prod** | `db.t3.small` | Enabled | 0.50 vCPU / 1024 MB | 2 (min 2, max 5) | ~$65 - $95 |

### 1-Command Deployment & Teardown
```bash
# Initialize and validate
make tf-init
make tf-validate

# Review plan & deploy to AWS
make tf-plan-dev
make tf-apply-dev

# Teardown to prevent ongoing cloud costs
make tf-destroy-dev
```

---

## 🧪 Testing & Code Quality

Run tests and linters locally before submitting pull requests:

```bash
# Run all 24 unit tests with coverage
make test

# Check code linting with Ruff
make lint

# Auto-format codebase
make format
```

All 24 unit tests verify:
- Feature preprocessing and ColumnTransformer pipeline encoding.
- Dynamic project root discovery and environment variable overrides.
- Precision@K ranking logic and Population Stability Index (PSI).
- Automated model promotion gate acceptance, rejection, and decision caching.
- Batch customer scoring and top risk driver explanations.
- High-risk volume anomaly spike detection and Slack/HTTP webhook alerts.
- FastAPI endpoints (`/health`, `/model-info`, `/predict`, `/predict-batch`, `/high-risk`).

---

## 🗺️ Roadmap

- [x] **Phase 1: Foundation** – Docker Compose (Postgres, MinIO, MLflow, Airflow), raw ingestion, dbt models, CI workflow.
- [x] **Phase 2: Features & Training** – Feature engineering pipeline, LightGBM training, MLflow tracking, automated promotion gate, drift checks.
- [x] **Phase 3: Scoring & Serving** – Daily batch Airflow DAG, FastAPI real-time/batch prediction endpoints, interactive Streamlit retention dashboard.
- [x] **Phase 4: Production Practices** – Automated GitHub Actions retraining trigger, Slack webhook alerts on high-risk spikes, multi-stage serving Docker container published to GHCR.
- [x] **Phase 5: Cloud Deployment** – Terraform IaC modules for AWS (ECS Fargate + RDS Postgres 15 + S3 + ALB), multi-environment dev/prod configurations, and automated Terraform CI.
