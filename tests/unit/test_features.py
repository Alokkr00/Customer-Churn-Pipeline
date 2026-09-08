"""Unit tests for data preprocessing and feature engineering."""

import numpy as np
import pandas as pd
import pytest

from src.data.ingest import clean_raw_data
from src.data.preprocess import preprocess_features
from src.features.feature_engineering import (
    build_preprocessor,
    extract_feature_matrix,
    filter_available_features,
)


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Provide synthetic raw customer records."""
    return pd.DataFrame(
        {
            "customerID": ["CUST-001", "CUST-002", "CUST-003", "CUST-004"],
            "gender": ["Female", "Male", "Male", "Female"],
            "SeniorCitizen": [0, 1, 0, 0],
            "Partner": ["Yes", "No", "No", "Yes"],
            "Dependents": ["No", "No", "Yes", "No"],
            "tenure": [1, 34, 2, 45],
            "PhoneService": ["No", "Yes", "Yes", "Yes"],
            "MultipleLines": ["No phone service", "No", "No", "Yes"],
            "InternetService": ["DSL", "DSL", "Fiber optic", "No"],
            "OnlineSecurity": ["No", "Yes", "Yes", "No internet service"],
            "OnlineBackup": ["Yes", "No", "Yes", "No internet service"],
            "DeviceProtection": ["No", "Yes", "No", "No internet service"],
            "TechSupport": ["No", "No", "No", "No internet service"],
            "StreamingTV": ["No", "No", "No", "No internet service"],
            "StreamingMovies": ["No", "No", "No", "No internet service"],
            "Contract": ["Month-to-month", "One year", "Month-to-month", "Two year"],
            "PaperlessBilling": ["Yes", "No", "Yes", "No"],
            "PaymentMethod": [
                "Electronic check",
                "Mailed check",
                "Bank transfer",
                "Credit card",
            ],
            "MonthlyCharges": [29.85, 56.95, 53.85, 42.30],
            "TotalCharges": ["29.85", "1889.5", "108.15", " "],  # whitespace test
            "Churn": ["No", "No", "Yes", "No"],
        }
    )


def test_clean_raw_data(sample_raw_df: pd.DataFrame):
    """Verify raw column renames, empty total_charges handling, and type casting."""
    cleaned = clean_raw_data(sample_raw_df)

    assert "customer_id" in cleaned.columns
    assert "monthly_charges" in cleaned.columns
    assert "total_charges" in cleaned.columns
    assert cleaned["total_charges"].iloc[3] == 0.0  # whitespace imputed to 0.0
    assert cleaned["tenure"].dtype == np.int64 or cleaned["tenure"].dtype == int


def test_preprocess_features(sample_raw_df: pd.DataFrame):
    """Verify binary mapping and derived features."""
    cleaned = clean_raw_data(sample_raw_df)
    processed = preprocess_features(cleaned)

    assert "churn_label" in processed.columns
    assert processed["churn_label"].iloc[2] == 1
    assert processed["churn_label"].iloc[0] == 0
    assert processed["has_partner"].iloc[0] == 1
    assert processed["has_partner"].iloc[1] == 0
    assert "charge_ratio" in processed.columns


def test_build_and_fit_preprocessor(sample_raw_df: pd.DataFrame):
    """Verify scikit-learn preprocessor pipeline fits and transforms cleanly."""
    cleaned = clean_raw_data(sample_raw_df)
    processed = preprocess_features(cleaned)

    num_cols, cat_cols, bin_cols = filter_available_features(processed)
    preprocessor = build_preprocessor(num_cols, cat_cols, bin_cols)

    feature_matrix, y, names = extract_feature_matrix(
        processed, preprocessor=preprocessor, is_training=True
    )

    assert feature_matrix.shape[0] == 4
    assert feature_matrix.shape[1] > 0
    assert not np.isnan(feature_matrix).any()
    assert len(y) == 4
    assert len(names) > 0
