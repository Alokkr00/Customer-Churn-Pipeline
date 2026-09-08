"""Data Ingestion Module.

Downloads the IBM Telco Customer Churn dataset and ingests it into
the `raw.telco_customers` table in PostgreSQL.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from sqlalchemy import create_engine, text

from src.utils.paths import DEFAULT_RAW_DATA_PATH, resolve_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATASET_URL = (
    "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/"
    "Telco-Customer-Churn.csv"
)

# Standard mapping from original CSV column names to Postgres snake_case
COLUMN_MAPPING = {
    "customerID": "customer_id",
    "gender": "gender",
    "SeniorCitizen": "senior_citizen",
    "Partner": "partner",
    "Dependents": "dependents",
    "tenure": "tenure",
    "PhoneService": "phone_service",
    "MultipleLines": "multiple_lines",
    "InternetService": "internet_service",
    "OnlineSecurity": "online_security",
    "OnlineBackup": "online_backup",
    "DeviceProtection": "device_protection",
    "TechSupport": "tech_support",
    "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_movies",
    "Contract": "contract",
    "PaperlessBilling": "paperless_billing",
    "PaymentMethod": "payment_method",
    "MonthlyCharges": "monthly_charges",
    "TotalCharges": "total_charges",
    "Churn": "churn",
}


def get_db_url() -> str:
    """Retrieve PostgreSQL connection string from environment."""
    return os.getenv(
        "CHURN_DB_URL",
        "postgresql://churn_user:churn_pass@localhost:5432/churn_db",
    )


def fetch_dataset(
    url: str = DATASET_URL,
    local_cache_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Download dataset or load from local cache if network is unavailable."""
    cache_file = resolve_path(local_cache_path) if local_cache_path else DEFAULT_RAW_DATA_PATH
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Attempting to download dataset from: {url}")
        df = pd.read_csv(url)
        df.to_csv(cache_file, index=False)
        logger.info(f"Downloaded and cached {len(df)} rows to {cache_file}")
        return df
    except Exception as exc:
        logger.warning(f"Failed to download from URL ({exc}). Checking local cache...")
        if cache_file.exists():
            logger.info(f"Loading dataset from local cache: {cache_file}")
            return pd.read_csv(cache_file)
        raise RuntimeError(
            f"Unable to fetch dataset from URL and local cache {cache_file} does not exist."
        ) from exc


def clean_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names and types for raw storage."""
    df_clean = df.rename(columns=COLUMN_MAPPING)

    # Ensure required columns are present
    missing_cols = set(COLUMN_MAPPING.values()) - set(df_clean.columns)
    if missing_cols:
        raise ValueError(f"Missing expected columns in raw data: {missing_cols}")

    # TotalCharges in IBM Telco has whitespace strings for new customers with 0 tenure
    df_clean["total_charges"] = pd.to_numeric(
        df_clean["total_charges"].astype(str).str.strip(), errors="coerce"
    ).fillna(0.0)

    # Ensure integer/float types
    df_clean["tenure"] = pd.to_numeric(df_clean["tenure"], errors="coerce").fillna(0).astype(int)
    df_clean["monthly_charges"] = pd.to_numeric(
        df_clean["monthly_charges"], errors="coerce"
    ).fillna(0.0)
    df_clean["senior_citizen"] = (
        pd.to_numeric(df_clean["senior_citizen"], errors="coerce").fillna(0).astype(int)
    )

    return df_clean


def ingest_to_postgres(
    df: pd.DataFrame,
    db_url: Optional[str] = None,
    schema: str = "raw",
    table_name: str = "telco_customers",
) -> int:
    """Load cleaned raw records into PostgreSQL raw schema."""
    target_url = db_url or get_db_url()
    logger.info(f"Connecting to database at {target_url.split('@')[-1]}...")
    engine = create_engine(target_url)

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))

    logger.info(f"Writing {len(df)} records to {schema}.{table_name}...")
    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists="replace",
        index=False,
        chunksize=1000,
    )
    logger.info("Ingestion completed successfully.")
    return len(df)


def run_ingestion() -> None:
    """Entrypoint to fetch and ingest raw customer churn data."""
    df_raw = fetch_dataset()
    df_cleaned = clean_raw_data(df_raw)
    ingest_to_postgres(df_cleaned)


if __name__ == "__main__":
    run_ingestion()
