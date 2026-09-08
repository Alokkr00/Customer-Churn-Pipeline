"""Feature Engineering Pipeline.

Defines transformer pipelines to encode categoricals, scale numerics,
and produce consistent feature matrices for training and inference.
"""

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Explicit feature definitions
NUMERIC_FEATURES: List[str] = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "total_services_count",
    "charge_consistency_ratio",
]

CATEGORICAL_FEATURES: List[str] = [
    "multiple_lines",
    "internet_service",
    "contract_type",
    "payment_method",
    "tenure_cohort",
]

BINARY_FEATURES: List[str] = [
    "is_male",
    "is_senior_citizen",
    "has_partner",
    "has_dependents",
    "has_phone_service",
    "has_online_security",
    "has_online_backup",
    "has_device_protection",
    "has_tech_support",
    "has_streaming_tv",
    "has_streaming_movies",
    "has_paperless_billing",
    "has_security_tech_pack",
    "has_streaming_bundle",
    "contract_risk_index",
    "is_electronic_check_payment",
    "is_high_monthly_charge",
]

TARGET_COLUMN = "churn_label"
ID_COLUMN = "customer_id"


def build_preprocessor(
    numeric_cols: List[str] = NUMERIC_FEATURES,
    categorical_cols: List[str] = CATEGORICAL_FEATURES,
    binary_cols: List[str] = BINARY_FEATURES,
) -> ColumnTransformer:
    """Build a ColumnTransformer for preprocessing all feature types."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    binary_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
            ("bin", binary_transformer, binary_cols),
        ],
        remainder="drop",
    )

    return preprocessor


def get_feature_and_target_columns() -> Tuple[List[str], str, str]:
    """Return lists of predictor columns, target column name, and id column name."""
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
    return feature_cols, TARGET_COLUMN, ID_COLUMN


def filter_available_features(
    df: pd.DataFrame,
    numeric_cols: List[str] = NUMERIC_FEATURES,
    categorical_cols: List[str] = CATEGORICAL_FEATURES,
    binary_cols: List[str] = BINARY_FEATURES,
) -> Tuple[List[str], List[str], List[str]]:
    """Filter declared features down to those actually present in DataFrame."""
    present_num = [c for c in numeric_cols if c in df.columns]
    present_cat = [c for c in categorical_cols if c in df.columns]
    present_bin = [c for c in binary_cols if c in df.columns]
    return present_num, present_cat, present_bin


def extract_feature_matrix(
    df: pd.DataFrame,
    preprocessor: ColumnTransformer,
    is_training: bool = False,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Transform input dataframe into model-ready matrix and target array."""
    # Ensure any missing numeric columns are created with default 0
    df_clean = df.copy()

    present_num, present_cat, present_bin = filter_available_features(df_clean)

    if is_training:
        feature_matrix = preprocessor.fit_transform(df_clean)
    else:
        feature_matrix = preprocessor.transform(df_clean)

    # Extract target if available
    y = df_clean[TARGET_COLUMN].to_numpy() if TARGET_COLUMN in df_clean.columns else np.array([])

    # Reconstruct output feature names for explainability
    cat_names = []
    if "cat" in preprocessor.named_transformers_:
        try:
            ohe = preprocessor.named_transformers_["cat"].named_steps["onehot"]
            cat_names = list(ohe.get_feature_names_out(present_cat))
        except Exception:
            cat_names = present_cat

    feature_names = present_num + cat_names + present_bin
    return np.asarray(feature_matrix, dtype=float), y, feature_names
