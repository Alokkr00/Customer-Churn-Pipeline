"""Data Preprocessing Module.

Cleans and prepares customer records, validates schema integrity,
and generates processed splits for offline testing and model consumption.
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from src.data.ingest import get_db_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BINARY_YES_NO_COLUMNS = [
    "partner",
    "dependents",
    "phone_service",
    "paperless_billing",
]


def load_from_raw_db(db_url: str = None) -> pd.DataFrame:
    """Load raw ingested records from PostgreSQL raw.telco_customers."""
    url = db_url or get_db_url()
    engine = create_engine(url)
    query = text("SELECT * FROM raw.telco_customers")
    logger.info("Extracting records from raw.telco_customers...")
    with engine.connect() as conn:
        return pd.read_sql_query(query, con=conn)


def preprocess_features(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize fields, convert Yes/No to 1/0, and engineer initial metrics."""
    df_proc = df.copy()

    # TotalCharges imputation and numeric coercion
    if "total_charges" in df_proc.columns:
        df_proc["total_charges"] = pd.to_numeric(
            df_proc["total_charges"].astype(str).str.strip(), errors="coerce"
        ).fillna(0.0)

    # Standardize column names if needed
    if "tenure" in df_proc.columns and "tenure_months" not in df_proc.columns:
        df_proc["tenure_months"] = df_proc["tenure"]
    if "contract" in df_proc.columns and "contract_type" not in df_proc.columns:
        df_proc["contract_type"] = df_proc["contract"]

    # Binary flags mapping
    binary_maps = {
        "partner": "has_partner",
        "dependents": "has_dependents",
        "phone_service": "has_phone_service",
        "paperless_billing": "has_paperless_billing",
    }
    for src_col, dest_col in binary_maps.items():
        if src_col in df_proc.columns:
            df_proc[dest_col] = (
                df_proc[src_col].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
            )

    # Add-on services to binary flags
    service_maps = {
        "online_security": "has_online_security",
        "online_backup": "has_online_backup",
        "device_protection": "has_device_protection",
        "tech_support": "has_tech_support",
        "streaming_tv": "has_streaming_tv",
        "streaming_movies": "has_streaming_movies",
    }
    for src_col, dest_col in service_maps.items():
        if src_col in df_proc.columns:
            df_proc[dest_col] = (
                df_proc[src_col].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
            )

    # Senior citizen flag
    if "senior_citizen" in df_proc.columns:
        df_proc["is_senior_citizen"] = df_proc["senior_citizen"].fillna(0).astype(int)

    # Standardize gender: Male -> 1, Female -> 0
    if "gender" in df_proc.columns:
        df_proc["is_male"] = df_proc["gender"].map({"Male": 1, "Female": 0}).fillna(0).astype(int)

    # Target column conversion: Yes -> 1, No -> 0
    if "churn" in df_proc.columns:
        df_proc["churn_label"] = (
            df_proc["churn"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
        )

    # Replace 'No internet service' or 'No phone service' with 'No'
    replace_cols = [
        "multiple_lines",
        "online_security",
        "online_backup",
        "device_protection",
        "tech_support",
        "streaming_tv",
        "streaming_movies",
    ]
    for col in replace_cols:
        if col in df_proc.columns:
            df_proc[col] = (
                df_proc[col]
                .replace({"No internet service": "No", "No phone service": "No"})
                .fillna("No")
            )

    # Tenure cohorts
    if "tenure_months" in df_proc.columns:
        df_proc["tenure_cohort"] = pd.cut(
            df_proc["tenure_months"],
            bins=[-1, 12, 24, 48, 120],
            labels=["0-12_months", "13-24_months", "25-48_months", "49+_months"],
        ).astype(str)

    # Risk indices & bundles
    if "contract_type" in df_proc.columns:
        df_proc["contract_risk_index"] = (
            df_proc["contract_type"]
            .map({"Month-to-month": 3, "One year": 2, "Two year": 1})
            .fillna(2)
            .astype(int)
        )

    if "payment_method" in df_proc.columns:
        df_proc["is_electronic_check_payment"] = (
            df_proc["payment_method"] == "Electronic check"
        ).astype(int)

    # Total services count
    active_service_flags = [c for c in service_maps.values() if c in df_proc.columns]
    if "has_phone_service" in df_proc.columns:
        active_service_flags.append("has_phone_service")
    if active_service_flags:
        df_proc["total_services_count"] = df_proc[active_service_flags].sum(axis=1)

    if "has_online_security" in df_proc.columns and "has_tech_support" in df_proc.columns:
        df_proc["has_security_tech_pack"] = (
            (df_proc["has_online_security"] == 1) & (df_proc["has_tech_support"] == 1)
        ).astype(int)

    if "has_streaming_tv" in df_proc.columns and "has_streaming_movies" in df_proc.columns:
        df_proc["has_streaming_bundle"] = (
            (df_proc["has_streaming_tv"] == 1) & (df_proc["has_streaming_movies"] == 1)
        ).astype(int)

    # Derived customer metrics
    if "monthly_charges" in df_proc.columns and "total_charges" in df_proc.columns:
        tenure_col = (
            df_proc["tenure_months"] if "tenure_months" in df_proc.columns else df_proc["tenure"]
        )
        expected_total = tenure_col * df_proc["monthly_charges"]
        df_proc["charge_ratio"] = np.where(
            expected_total > 0,
            df_proc["total_charges"] / (expected_total + 1e-5),
            1.0,
        )
        df_proc["charge_consistency_ratio"] = df_proc["charge_ratio"]
        df_proc["is_high_monthly_charge"] = (df_proc["monthly_charges"] >= 70.0).astype(int)

    return df_proc


def train_test_split_dataset(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform stratified split based on target label if available."""
    from sklearn.model_selection import train_test_split

    stratify_col = df["churn_label"] if "churn_label" in df.columns else None
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_col,
    )
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def run_preprocessing() -> None:
    """Run data extraction, preprocessing and write to staging table in postgres."""
    df_raw = load_from_raw_db()
    df_proc = preprocess_features(df_raw)
    engine = create_engine(get_db_url())

    logger.info("Writing preprocessed data to staging.customers_clean...")
    df_proc.to_sql(
        name="customers_clean",
        con=engine,
        schema="staging",
        if_exists="replace",
        index=False,
    )
    logger.info("Preprocessing complete.")


if __name__ == "__main__":
    run_preprocessing()
