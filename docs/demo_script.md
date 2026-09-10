# 🎬 Customer Churn Pipeline: 3-Minute Video Demo Script

A structured presentation script for recording a high-impact portfolio video, technical demo, or stakeholder walkthrough.

---

## ⏱️ Timeline & Speaking Points

### 0:00 - 0:30 | Business Problem & High-Level Architecture
* **Screen**: GitHub repository homepage with passing badges & architecture diagram.
* **Speaking Points**:
  > "Customer churn directly damages revenue in subscription businesses, where acquiring a new customer costs 5 to 7 times more than retaining an existing one. Today I'm walking through an end-to-end MLOps and data engineering pipeline that predicts churn risk daily, isolates root causes, and triggers automated retention campaigns."
  > "The architecture connects raw PostgreSQL data ingestion, dbt transformation marts, MLflow experiment tracking with automated promotion gates, daily batch scoring in Airflow, real-time sub-30ms FastAPI serving, and an interactive Streamlit retention portal."

---

### 0:30 - 1:15 | Data Engineering & Model Governance
* **Screen**: Docker Compose terminal (`docker compose ps`), dbt docs / lineage, and MLflow UI (`http://localhost:5000`).
* **Speaking Points**:
  > "Our data pipeline ingests raw customer events into PostgreSQL, transformed across staging, intermediate, and marts layers using dbt with schema constraint testing."
  > "For modeling, we benchmark a baseline Logistic Regression against a gradient-boosted LightGBM champion. We track hyperparameters and PR-AUC in MLflow. Before any candidate reaches production, an automated gate in `evaluate.py` verifies two strict criteria: an ROC-AUC improvement of at least 1% and a Population Stability Index under 0.10 to prevent model drift."

---

### 1:15 - 2:00 | Real-Time Serving & Explainable AI (FastAPI)
* **Screen**: FastAPI Swagger docs (`http://localhost:8000/docs`), executing a POST `/predict` request.
* **Speaking Points**:
  > "In production, our model serves predictions via FastAPI with sub-30 millisecond latency. Rather than just returning a probability score, each response diagnoses the top risk drivers—such as month-to-month contracts, lack of tech support, or electronic check billing—and pairs them with targeted retention actions, like offering a 15% discount for a 12-month contract lock-in."

---

### 2:00 - 2:35 | Interactive Retention Hub & "What-If" Simulator
* **Screen**: Streamlit Retention Hub (`http://localhost:8501`).
* **Speaking Points**:
  > "Retention specialists and customer success teams use our interactive Streamlit dashboard. The Executive Overview displays total accounts and monthly revenue at risk."
  > "The 'What-If' Simulator lets account managers test retention strategies live. For example, by simulating a contract extension from month-to-month to one year or adding a complimentary security pack, the predicted churn probability drops from 81% down to 24% in real-time."

---

### 2:35 - 3:00 | CI/CD, Container Publishing & Cloud IaC (Terraform)
* **Screen**: GitHub Actions workflow runs (all green ✅), GHCR package page, and `infra/` folder.
* **Speaking Points**:
  > "The system is fully automated. Pull requests trigger linting, formatting, dbt validation, and 24 unit tests. Every Monday, a GitHub Actions workflow retrains the model, promotes winners, and publishes multi-stage Docker images to GitHub Container Registry."
  > "Finally, the entire AWS infrastructure—including VPC networking, RDS PostgreSQL, S3 artifact buckets, and auto-scaling ECS Fargate clusters—is provisioned with modular Terraform across dev and prod environments."
  > "Thank you! The complete code and documentation are open source on GitHub."
