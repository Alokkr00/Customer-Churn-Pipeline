"""Batch Customer Churn Scoring Engine.

Loads the active production model, scores active customers,
assigns risk tiers, identifies top churn risk drivers, and persists
results to the PostgreSQL scoring schema and local reports.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine, text

from src.data.ingest import get_db_url
from src.features.feature_engineering import (
    ID_COLUMN,
    filter_available_features,
)
from src.training.train import load_training_data
from src.utils.paths import (
    CANDIDATE_MODEL_PATH,
    PROD_MODEL_PATH,
    REPORTS_DIR,
    resolve_path,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HIGH_RISK_THRESHOLD = 0.65
MEDIUM_RISK_THRESHOLD = 0.35
HIGH_RISK_EXPORT_PATH = REPORTS_DIR / "high_risk_customers.csv"


def load_scoring_model() -> Tuple[Pipeline, str]:
    """Load production model or fallback to candidate model."""
    if PROD_MODEL_PATH.exists():
        logger.info(f"Loading production model from: {PROD_MODEL_PATH}")
        return joblib.load(PROD_MODEL_PATH), "production_v1"
    if CANDIDATE_MODEL_PATH.exists():
        logger.warning(f"Production model not found. Using candidate model from: {CANDIDATE_MODEL_PATH}")
        return joblib.load(CANDIDATE_MODEL_PATH), "candidate_v1"
    raise FileNotFoundError("No trained model found. Run 'make train' or 'make evaluate' first.")


def assign_risk_tier(probability: float) -> str:
    """Categorize churn probability into business risk tier."""
    if probability >= HIGH_RISK_THRESHOLD:
        return "High"
    if probability >= MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def extract_top_risk_drivers(row: pd.Series) -> List[str]:
    """Identify top interpretable business risk factors driving customer churn propensity."""
    drivers = []

    # Contract Type Risk
    contract = str(row.get("contract_type", row.get("contract", "")))
    if contract == "Month-to-month":
        drivers.append("Month-to-month contract (low lock-in)")

    # Tenure Vulnerability
    tenure = float(row.get("tenure_months", row.get("tenure", 0)))
    if tenure <= 12:
        drivers.append("New customer in high-vulnerability first year")

    # Payment Method Friction
    payment = str(row.get("payment_method", ""))
    if payment == "Electronic check":
        drivers.append("Electronic check payment (higher historic default & churn)")

    # Support & Security Gaps
    has_tech = int(row.get("has_tech_support", 0))
    if not has_tech:
        drivers.append("No active Tech Support subscription")

    has_sec = int(row.get("has_online_security", 0))
    internet = str(row.get("internet_service", ""))
    if internet == "Fiber optic" and not has_sec:
        drivers.append("High-speed Fiber without Online Security pack")

    # High Price Sensitivity
    charges = float(row.get("monthly_charges", 0.0))
    if charges >= 75.0:
        drivers.append(f"High monthly recurring charges (${charges:.2f}/mo)")

    # Service Count Stickiness
    services_count = float(row.get("total_services_count", 0))
    if 0 < services_count <= 2:
        drivers.append("Low ecosystem adoption (<= 2 subscribed services)")

    if not drivers:
        drivers.append("Standard tenure pattern")

    return drivers[:3]


def score_customers(
    df: pd.DataFrame,
    model: Optional[Pipeline] = None,
    model_version: str = "production_v1",
) -> pd.DataFrame:
    """Score all customers in dataframe, generate probabilities, tiers, and risk reasons."""
    scoring_model = model
    if scoring_model is None:
        scoring_model, model_version = load_scoring_model()

    df_clean = df.copy()
    num_cols, cat_cols, bin_cols = filter_available_features(df_clean)
    feature_cols = num_cols + cat_cols + bin_cols

    X = df_clean[feature_cols]

    # Predict churn probability (Class 1)
    probabilities = scoring_model.predict_proba(X)[:, 1]

    # Build output dataframe
    customer_ids = df_clean[ID_COLUMN] if ID_COLUMN in df_clean.columns else [f"CUST-{i:05d}" for i in range(len(df_clean))]

    results = []
    now_utc = datetime.now(timezone.utc)

    for idx, prob in enumerate(probabilities):
        row = df_clean.iloc[idx]
        cid = customer_ids.iloc[idx] if hasattr(customer_ids, "iloc") else customer_ids[idx]
        risk_tier = assign_risk_tier(prob)
        drivers = extract_top_risk_drivers(row)

        results.append(
            {
                "customer_id": cid,
                "churn_probability": round(float(prob), 4),
                "risk_tier": risk_tier,
                "top_reasons": json.dumps(drivers),
                "model_version": model_version,
                "monthly_charges": float(row.get("monthly_charges", 0.0)),
                "tenure_months": int(row.get("tenure_months", row.get("tenure", 0))),
                "contract_type": str(row.get("contract_type", row.get("contract", "Unknown"))),
                "scored_at": now_utc,
            }
        )

    scored_df = pd.DataFrame(results)
    return scored_df


def persist_scores_to_db(
    scored_df: pd.DataFrame,
    db_url: Optional[str] = None,
    schema: str = "scoring",
    table_name: str = "churn_scores",
) -> None:
    """Save scored customer records to PostgreSQL."""
    target_url = db_url or get_db_url()
    try:
        engine = create_engine(target_url)
        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))

        # Save primary columns matching schema
        db_columns = [
            "customer_id",
            "churn_probability",
            "risk_tier",
            "top_reasons",
            "model_version",
            "scored_at",
        ]
        subset = scored_df[db_columns]
        logger.info(f"Writing {len(subset)} scored records to {schema}.{table_name}...")
        subset.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists="append",
            index=False,
            chunksize=1000,
        )
        logger.info("Scores successfully written to PostgreSQL.")
    except Exception as exc:
        logger.warning(f"Could not persist scores to database ({exc}).")


def run_batch_scoring(
    export_csv: bool = True,
    output_csv_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute end-to-end customer scoring, database write, and high-risk CSV export."""
    logger.info("Starting batch customer churn scoring...")
    raw_df = load_training_data()
    scored_df = score_customers(raw_df)

    # Persist to database
    persist_scores_to_db(scored_df)

    # Export high-risk customers to CSV
    high_risk_df = scored_df[scored_df["risk_tier"] == "High"].sort_values(
        by="churn_probability", ascending=False
    )

    if export_csv:
        target_path = resolve_path(output_csv_path) if output_csv_path else HIGH_RISK_EXPORT_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        high_risk_df.to_csv(target_path, index=False)
        logger.info(f"Exported {len(high_risk_df)} high-risk customers to {target_path}")

    high_risk_count = len(high_risk_df)
    total_count = len(scored_df)
    high_risk_pct = round(high_risk_count / max(1, total_count) * 100, 2)
    avg_churn_prob = round(float(scored_df["churn_probability"].mean()), 4)

    summary = {
        "total_customers_scored": total_count,
        "high_risk_customers": high_risk_count,
        "high_risk_percentage": high_risk_pct,
        "average_churn_probability": avg_churn_prob,
        "high_risk_export_path": str(HIGH_RISK_EXPORT_PATH),
    }

    logger.info(
        f"Scoring complete. Scored: {total_count} | High Risk: {high_risk_count} ({high_risk_pct}%) | "
        f"Avg Prob: {avg_churn_prob:.4f}"
    )

    return summary


if __name__ == "__main__":
    summary = run_batch_scoring()
    print("\n--- Churn Scoring Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
