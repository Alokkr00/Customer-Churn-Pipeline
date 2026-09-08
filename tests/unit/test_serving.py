"""Unit tests for FastAPI Serving Endpoints."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.serving.main import app, model_state
from tests.unit.test_evaluate import DummyClassifier


@pytest.fixture(autouse=True)
def inject_mock_model():
    """Ensure a loaded model is available for testing without depending on disk artifacts."""
    mock_clf = DummyClassifier(custom_proba=np.array([0.75]))
    model_state["model"] = mock_clf
    model_state["version"] = "test_mock_v1"
    model_state["model_type"] = "DummyClassifier"
    yield
    model_state["model"] = None


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client."""
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    """Verify /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_version"] == "test_mock_v1"


def test_model_info_endpoint(client: TestClient):
    """Verify /model-info returns metadata."""
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "customer_churn_classifier"
    assert data["is_loaded"] is True


def test_predict_endpoint_single_customer(client: TestClient):
    """Verify /predict returns valid schema, probability, and retention recommendation."""
    payload = {
        "customer_id": "TEST-CUST-101",
        "gender": "Female",
        "senior_citizen": 0,
        "partner": "No",
        "dependents": "No",
        "tenure_months": 4,
        "phone_service": "Yes",
        "multiple_lines": "No",
        "internet_service": "Fiber optic",
        "online_security": "No",
        "online_backup": "No",
        "device_protection": "No",
        "tech_support": "No",
        "streaming_tv": "No",
        "streaming_movies": "No",
        "contract_type": "Month-to-month",
        "paperless_billing": "Yes",
        "payment_method": "Electronic check",
        "monthly_charges": 85.00,
        "total_charges": 340.00,
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["customer_id"] == "TEST-CUST-101"
    assert "churn_probability" in data
    assert "risk_tier" in data
    assert "top_risk_drivers" in data
    assert "recommended_retention_action" in data
    assert isinstance(data["top_risk_drivers"], list)
    assert data["latency_ms"] >= 0.0


def test_predict_batch_endpoint(client: TestClient):
    """Verify /predict-batch accepts and processes multiple customer records."""
    customer_1 = {
        "customer_id": "BATCH-001",
        "tenure_months": 2,
        "contract_type": "Month-to-month",
        "internet_service": "Fiber optic",
        "monthly_charges": 90.0,
    }
    customer_2 = {
        "customer_id": "BATCH-002",
        "tenure_months": 48,
        "contract_type": "Two year",
        "internet_service": "DSL",
        "monthly_charges": 45.0,
    }

    payload = {"customers": [customer_1, customer_2]}
    response = client.post("/predict-batch", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_customers"] == 2
    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["customer_id"] == "BATCH-001"
    assert data["predictions"][1]["customer_id"] == "BATCH-002"


def test_high_risk_endpoint(client: TestClient):
    """Verify /high-risk endpoint returns valid response structure."""
    response = client.get("/high-risk?threshold=0.60&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total_high_risk" in data
    assert "customers" in data
    assert data["threshold"] == 0.60
