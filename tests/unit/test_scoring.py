"""Unit tests for Customer Churn Scoring and Explainability Engine."""

import json

import numpy as np
import pandas as pd

from src.scoring.score import (
    assign_risk_tier,
    extract_top_risk_drivers,
    score_customers,
)
from tests.unit.test_evaluate import DummyClassifier


def test_assign_risk_tier():
    """Verify tier assignment boundaries."""
    assert assign_risk_tier(0.85) == "High"
    assert assign_risk_tier(0.65) == "High"
    assert assign_risk_tier(0.64) == "Medium"
    assert assign_risk_tier(0.35) == "Medium"
    assert assign_risk_tier(0.34) == "Low"
    assert assign_risk_tier(0.05) == "Low"


def test_extract_top_risk_drivers():
    """Verify that vulnerable customer patterns trigger appropriate explanations."""
    vulnerable_customer = pd.Series(
        {
            "contract_type": "Month-to-month",
            "tenure_months": 3,
            "monthly_charges": 89.50,
            "payment_method": "Electronic check",
            "has_tech_support": 0,
            "internet_service": "Fiber optic",
            "has_online_security": 0,
            "total_services_count": 1,
        }
    )

    drivers = extract_top_risk_drivers(vulnerable_customer)
    assert len(drivers) <= 3
    assert any("Month-to-month" in d for d in drivers)
    assert any("first year" in d or "tenure" in d.lower() for d in drivers)


def test_score_customers_output_structure():
    """Verify scored dataframe columns and types."""
    sample_df = pd.DataFrame(
        {
            "customer_id": ["CUST-001", "CUST-002"],
            "tenure_months": [5, 40],
            "monthly_charges": [80.0, 40.0],
            "total_charges": [400.0, 1600.0],
            "total_services_count": [2, 5],
            "charge_consistency_ratio": [1.0, 1.0],
            "multiple_lines": ["No", "Yes"],
            "internet_service": ["Fiber optic", "DSL"],
            "contract_type": ["Month-to-month", "Two year"],
            "payment_method": ["Electronic check", "Credit card"],
            "tenure_cohort": ["0-12_months", "25-48_months"],
            "is_male": [1, 0],
            "is_senior_citizen": [0, 0],
            "has_partner": [0, 1],
            "has_dependents": [0, 1],
            "has_phone_service": [1, 1],
            "has_online_security": [0, 1],
            "has_online_backup": [0, 1],
            "has_device_protection": [0, 1],
            "has_tech_support": [0, 1],
            "has_streaming_tv": [1, 0],
            "has_streaming_movies": [1, 0],
            "has_paperless_billing": [1, 0],
            "has_security_tech_pack": [0, 1],
            "has_streaming_bundle": [1, 0],
            "contract_risk_index": [3, 1],
            "is_electronic_check_payment": [1, 0],
            "is_high_monthly_charge": [1, 0],
        }
    )

    dummy_model = DummyClassifier(custom_proba=np.array([0.80, 0.20]))
    scored = score_customers(sample_df, model=dummy_model, model_version="test_v1")

    assert len(scored) == 2
    assert "churn_probability" in scored.columns
    assert "risk_tier" in scored.columns
    assert "top_reasons" in scored.columns
    assert scored["risk_tier"].iloc[0] == "High"
    assert scored["risk_tier"].iloc[1] == "Low"

    reasons = json.loads(scored["top_reasons"].iloc[0])
    assert isinstance(reasons, list)
    assert len(reasons) > 0
