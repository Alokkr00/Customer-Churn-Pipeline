"""Unit tests for evaluation metrics and automated model promotion logic."""

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin

from src.training.evaluate import (
    calculate_simple_drift_score,
    evaluate_and_promote,
)
from src.training.train import compute_metrics, compute_precision_at_k


class DummyClassifier(BaseEstimator, ClassifierMixin):
    """Predictable dummy model for testing promotion logic."""

    def __init__(self, proba_offset: float = 0.0, custom_proba: np.ndarray = None):
        self.proba_offset = proba_offset
        self.custom_proba = custom_proba

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        if self.custom_proba is not None:
            p = np.asarray(self.custom_proba)
            return np.column_stack([1 - p, p])
        n = len(X)
        # Create base probabilities around 0.3 + offset
        base = np.linspace(0.1, 0.8, n) + self.proba_offset
        base = np.clip(base, 0.01, 0.99)
        return np.column_stack([1 - base, base])

    def predict(self, X):
        proba = self.predict_proba(X)[:, 1]
        return (proba >= 0.5).astype(int)


@pytest.fixture
def eval_dataset() -> pd.DataFrame:
    """Provide synthetic validation dataframe."""
    np.random.seed(42)
    n = 100
    y = np.random.binomial(1, 0.3, n)
    # Ensure positive examples exist
    y[0:10] = 1
    y[10:20] = 0

    return pd.DataFrame(
        {
            "customer_id": [f"CUST-{i:03d}" for i in range(n)],
            "tenure_months": np.random.randint(1, 72, n),
            "monthly_charges": np.random.uniform(20.0, 100.0, n),
            "total_charges": np.random.uniform(20.0, 5000.0, n),
            "total_services_count": np.random.randint(1, 8, n),
            "charge_consistency_ratio": np.ones(n),
            "multiple_lines": ["No"] * n,
            "internet_service": ["DSL"] * n,
            "contract_type": ["Month-to-month"] * n,
            "payment_method": ["Electronic check"] * n,
            "tenure_cohort": ["0-12_months"] * n,
            "is_male": [1] * n,
            "is_senior_citizen": [0] * n,
            "has_partner": [1] * n,
            "has_dependents": [0] * n,
            "has_phone_service": [1] * n,
            "has_online_security": [0] * n,
            "has_online_backup": [0] * n,
            "has_device_protection": [0] * n,
            "has_tech_support": [0] * n,
            "streaming_tv": ["No"] * n,
            "streaming_movies": ["No"] * n,
            "has_paperless_billing": [1] * n,
            "has_security_tech_pack": [0] * n,
            "has_streaming_bundle": [0] * n,
            "contract_risk_index": [3] * n,
            "is_electronic_check_payment": [1] * n,
            "is_high_monthly_charge": [0] * n,
            "churn_label": y,
        }
    )


def test_precision_at_k():
    """Verify Precision@K ranking logic."""
    y_true = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    y_proba = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])

    # Top 20% is top 2 instances: both are 1 -> Precision@20% = 1.0
    p20 = compute_precision_at_k(y_true, y_proba, k_pct=0.2)
    assert p20 == 1.0

    # Inverted ranking
    p20_bad = compute_precision_at_k(y_true, 1 - y_proba, k_pct=0.2)
    assert p20_bad == 0.0


def test_compute_metrics():
    """Verify metrics dictionary keys and reasonable values."""
    y_true = np.array([1, 0, 1, 0, 1, 0])
    y_proba = np.array([0.8, 0.2, 0.7, 0.3, 0.9, 0.1])
    metrics = compute_metrics(y_true, y_proba)

    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "f1_score" in metrics
    assert metrics["roc_auc"] == 1.0


def test_calculate_simple_drift_score():
    """Verify PSI calculation for identical vs shifted distributions."""
    dist_a = np.random.uniform(0.2, 0.8, 1000)
    # Identical distribution should have very low PSI
    psi_low = calculate_simple_drift_score(dist_a, dist_a)
    assert psi_low < 0.01

    # Shifted distribution should have higher PSI
    dist_b = np.random.uniform(0.7, 0.95, 1000)
    psi_high = calculate_simple_drift_score(dist_a, dist_b)
    assert psi_high > 0.10


def test_promotion_gate_logic(eval_dataset: pd.DataFrame):
    """Test model promotion decision logic with candidate vs production models."""
    cand = DummyClassifier(proba_offset=0.0)
    prod = DummyClassifier(proba_offset=0.0)

    # Identical performance: should NOT promote because delta is 0 < 0.01
    decision = evaluate_and_promote(
        candidate_pipeline=cand,
        production_pipeline=prod,
        eval_df=eval_dataset,
        auc_delta_required=0.01,
    )
    assert decision["promoted"] is False

    # Candidate significantly better (+0.05 AUC required delta = 0.01)
    y = eval_dataset["churn_label"].to_numpy()
    base_prod_proba = np.linspace(0.2, 0.7, len(y))
    poor_prod = DummyClassifier(custom_proba=base_prod_proba)

    cand_proba = np.clip(base_prod_proba + (y - 0.5) * 0.3, 0.05, 0.95)
    better_cand = DummyClassifier(custom_proba=cand_proba)

    decision_promoted = evaluate_and_promote(
        candidate_pipeline=better_cand,
        production_pipeline=poor_prod,
        eval_df=eval_dataset,
        auc_delta_required=0.01,
        max_drift_allowed=1.0,
    )
    assert decision_promoted["promoted"] is True
    assert decision_promoted["auc_delta"] > 0.01

    # Rejected when drift exceeds threshold
    decision_rejected_drift = evaluate_and_promote(
        candidate_pipeline=better_cand,
        production_pipeline=poor_prod,
        eval_df=eval_dataset,
        auc_delta_required=0.01,
        max_drift_allowed=0.0001,
    )
    assert decision_rejected_drift["promoted"] is False
