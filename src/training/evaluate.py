"""Model Evaluation and Quality Gate Promotion Module.

Evaluates candidate models against active production models,
checks performance deltas and drift thresholds, and promotes models in MLflow.
"""

import logging
import os
from typing import Any, Dict, Optional

import joblib
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline

from src.features.feature_engineering import (
    TARGET_COLUMN,
    filter_available_features,
)
from src.training.train import (
    TRACKING_URI,
    compute_metrics,
    load_training_data,
    train_test_split_dataset,
)
from src.utils.paths import CANDIDATE_MODEL_PATH, MODELS_DIR, PROD_MODEL_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AUC_IMPROVEMENT_THRESHOLD = float(os.getenv("AUC_IMPROVEMENT_THRESHOLD", "0.01"))
DRIFT_PSI_THRESHOLD = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.10"))
COLD_START_MIN_AUC = 0.70


def load_candidate_model() -> Pipeline:
    """Load latest candidate model from disk or raise error."""
    if not CANDIDATE_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Candidate model artifact not found at {CANDIDATE_MODEL_PATH}. Run training first."
        )
    return joblib.load(CANDIDATE_MODEL_PATH)


def load_production_model() -> Optional[Pipeline]:
    """Load currently active production model from disk or MLflow."""
    # First check disk cache
    if PROD_MODEL_PATH.exists():
        logger.info(f"Loading active production model from local cache: {PROD_MODEL_PATH}")
        return joblib.load(PROD_MODEL_PATH)

    # Attempt to load from MLflow Model Registry
    try:
        client = MlflowClient(tracking_uri=TRACKING_URI)
        model_name = "churn_champion"
        latest_prod = client.get_latest_versions(model_name, stages=["Production"])
        if latest_prod:
            prod_uri = f"models:/{model_name}/Production"
            logger.info(f"Loading production model from MLflow registry: {prod_uri}")
            return mlflow.sklearn.load_model(prod_uri)
    except Exception as exc:
        logger.info(f"No existing production model found in MLflow registry: {exc}")

    return None


def calculate_simple_drift_score(
    ref_distribution: np.ndarray, curr_distribution: np.ndarray, num_bins: int = 10
) -> float:
    """Calculate Population Stability Index (PSI) between two probability distributions."""
    if len(ref_distribution) == 0 or len(curr_distribution) == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, num_bins + 1)
    ref_counts, _ = np.histogram(ref_distribution, bins=bins)
    curr_counts, _ = np.histogram(curr_distribution, bins=bins)

    # Standard Laplace +1 smoothing to avoid infinite values for empty bins
    ref_pct = (ref_counts + 1.0) / (np.sum(ref_counts) + num_bins)
    curr_pct = (curr_counts + 1.0) / (np.sum(curr_counts) + num_bins)

    psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
    return float(psi)


def evaluate_and_promote(
    candidate_pipeline: Optional[Pipeline] = None,
    production_pipeline: Optional[Pipeline] = None,
    eval_df: Optional[pd.DataFrame] = None,
    auc_delta_required: float = AUC_IMPROVEMENT_THRESHOLD,
    max_drift_allowed: float = DRIFT_PSI_THRESHOLD,
) -> Dict[str, Any]:
    """Execute evaluation gate and decide whether to promote candidate model."""
    candidate = candidate_pipeline or load_candidate_model()
    production = production_pipeline if production_pipeline is not None else load_production_model()

    # Load validation data
    if eval_df is None:
        full_df = load_training_data()
        _, val_df = train_test_split_dataset(full_df, test_size=0.2, random_state=42)
    else:
        val_df = eval_df

    num_cols, cat_cols, bin_cols = filter_available_features(val_df)
    feature_cols = num_cols + cat_cols + bin_cols
    X_val = val_df[feature_cols]
    y_val = val_df[TARGET_COLUMN].to_numpy()

    # Candidate evaluation
    candidate_proba = candidate.predict_proba(X_val)[:, 1]
    candidate_metrics = compute_metrics(y_val, candidate_proba)
    candidate_auc = candidate_metrics["roc_auc"]

    # Cold Start scenario: No production model exists yet
    if production is None:
        logger.info(
            f"Cold Start: No active production model found. Candidate AUC is {candidate_auc:.4f}."
        )
        should_promote = candidate_auc >= COLD_START_MIN_AUC
        reason = (
            f"Initial model meets cold-start quality threshold (>={COLD_START_MIN_AUC})"
            if should_promote
            else f"Initial model AUC ({candidate_auc:.4f}) below minimum threshold ({COLD_START_MIN_AUC})"
        )
        drift_score = 0.0
        prod_metrics = None
        auc_delta = candidate_auc
    else:
        # Production model evaluation
        prod_proba = production.predict_proba(X_val)[:, 1]
        prod_metrics = compute_metrics(y_val, prod_proba)
        production_auc = prod_metrics["roc_auc"]
        auc_delta = candidate_auc - production_auc

        # Data / prediction drift check
        drift_score = calculate_simple_drift_score(prod_proba, candidate_proba)

        # Core Promotion Logic:
        # candidate_auc >= production_auc + 0.01 AND drift_score <= threshold
        auc_passes = auc_delta >= auc_delta_required
        drift_passes = drift_score <= max_drift_allowed
        should_promote = auc_passes and drift_passes

        if should_promote:
            reason = (
                f"Candidate outperforms Production (+{auc_delta:.4f} AUC >= +{auc_delta_required}) "
                f"with acceptable drift ({drift_score:.4f} <= {max_drift_allowed})"
            )
        else:
            reasons = []
            if not auc_passes:
                reasons.append(
                    f"AUC improvement (+{auc_delta:.4f}) did not meet +{auc_delta_required} gate"
                )
            if not drift_passes:
                reasons.append(f"Drift score ({drift_score:.4f}) exceeded {max_drift_allowed}")
            reason = "Rejected: " + "; ".join(reasons)

    # Perform promotion if approved
    if should_promote:
        logger.info(f"PROMOTING MODEL: {reason}")
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(candidate, PROD_MODEL_PATH)
        logger.info(f"Production model cached to {PROD_MODEL_PATH}")

        # Register in MLflow if active
        try:
            client = MlflowClient(tracking_uri=TRACKING_URI)
            client.transition_model_version_stage(
                name="churn_champion",
                version="1",
                stage="Production",
                archive_existing_versions=True,
            )
        except Exception:
            pass
    else:
        logger.info(f"KEEPING CURRENT PRODUCTION MODEL: {reason}")

    decision = {
        "promoted": should_promote,
        "reason": reason,
        "candidate_auc": candidate_auc,
        "production_auc": prod_metrics["roc_auc"] if prod_metrics else None,
        "auc_delta": auc_delta,
        "drift_psi_score": drift_score,
        "candidate_metrics": candidate_metrics,
        "production_metrics": prod_metrics,
    }

    return decision


if __name__ == "__main__":
    result = evaluate_and_promote()
    print("\n--- Model Promotion Decision ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
