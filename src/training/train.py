"""Model Training Module.

Trains baseline Logistic Regression and champion LightGBM classifiers,
computes classification metrics and Precision@K, and logs all artifacts to MLflow.
"""

import logging
import os
from typing import Any, Dict, Tuple

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine

from src.data.ingest import clean_raw_data, fetch_dataset, get_db_url
from src.data.preprocess import preprocess_features, train_test_split_dataset
from src.features.feature_engineering import (
    TARGET_COLUMN,
    build_preprocessor,
    filter_available_features,
)
from src.utils.paths import CANDIDATE_MODEL_PATH, MODELS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "customer_churn_prediction")
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def load_training_data(db_url: str = None) -> pd.DataFrame:
    """Load features from marts table or fallback to clean pipeline on local CSV."""
    url = db_url or get_db_url()
    try:
        engine = create_engine(url)
        query = "SELECT * FROM marts.mart_churn_features"
        logger.info("Attempting to load features from marts.mart_churn_features in PostgreSQL...")
        df = pd.read_sql_query(query, con=engine)
        if len(df) > 0:
            logger.info(f"Successfully loaded {len(df)} records from marts table.")
            return df
    except Exception as exc:
        logger.warning(
            f"Could not load from marts table ({exc}). Falling back to local data pipeline."
        )

    # Fallback: ingest & preprocess directly
    df_raw = fetch_dataset()
    df_clean = clean_raw_data(df_raw)
    df_proc = preprocess_features(df_clean)
    return df_proc


def compute_precision_at_k(y_true: np.ndarray, y_proba: np.ndarray, k_pct: float = 0.2) -> float:
    """Calculate Precision@K for the top K% highest churn probability customers."""
    if len(y_true) == 0:
        return 0.0
    n = len(y_true)
    k_count = max(1, int(n * k_pct))

    # Sort descending by predicted probability
    top_indices = np.argsort(y_proba)[::-1][:k_count]
    top_labels = y_true[top_indices]
    precision_k = float(np.mean(top_labels))
    return precision_k


def compute_metrics(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """Compute comprehensive classification metrics."""
    y_pred = (y_proba >= threshold).astype(int)
    roc_auc = float(roc_auc_score(y_true, y_proba))
    pr_auc = float(average_precision_score(y_true, y_proba))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    p_at_10 = compute_precision_at_k(y_true, y_proba, k_pct=0.10)
    p_at_20 = compute_precision_at_k(y_true, y_proba, k_pct=0.20)

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "f1_score": f1,
        "precision": prec,
        "recall": rec,
        "precision_at_10_pct": p_at_10,
        "precision_at_20_pct": p_at_20,
    }


def train_single_model(
    model_name: str,
    estimator: Any,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    preprocessor: Any,
) -> Tuple[Pipeline, Dict[str, float]]:
    """Train pipeline, calculate metrics, and log everything to MLflow."""
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", estimator),
        ]
    )

    pipeline.fit(X_train, y_train)

    # Probabilities for positive class (Churn)
    val_proba = pipeline.predict_proba(X_val)[:, 1]
    metrics = compute_metrics(y_val, val_proba)

    logger.info(
        f"[{model_name}] Val ROC-AUC: {metrics['roc_auc']:.4f} | "
        f"Precision@20%: {metrics['precision_at_20_pct']:.4f} | F1: {metrics['f1_score']:.4f}"
    )

    try:
        with mlflow.start_run(run_name=model_name, nested=True):
            mlflow.log_param("model_name", model_name)
            mlflow.log_params(estimator.get_params())
            mlflow.log_metrics(metrics)
            mlflow.set_tag("pipeline_stage", "candidate_training")

            # Log sklearn pipeline
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                artifact_path="model",
                registered_model_name=f"churn_{model_name.lower().replace(' ', '_')}",
            )
    except Exception as exc:
        logger.warning(f"MLflow logging skipped or unavailable ({exc}).")

    return pipeline, metrics


def run_training() -> Dict[str, Any]:
    """Execute full model training pipeline for baseline and candidate models."""
    df = load_training_data()

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataframe.")

    train_df, val_df = train_test_split_dataset(df, test_size=0.2, random_state=42)

    # Filter features available in this dataset
    num_cols, cat_cols, bin_cols = filter_available_features(train_df)
    preprocessor = build_preprocessor(num_cols, cat_cols, bin_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COLUMN].to_numpy()

    X_val = val_df[feature_cols]
    y_val = val_df[TARGET_COLUMN].to_numpy()

    # Configure MLflow
    try:
        mlflow.set_tracking_uri(TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
    except Exception as e:
        logger.warning(f"Could not connect to MLflow tracking server: {e}")

    # Baseline Model: Logistic Regression
    lr_estimator = LogisticRegression(
        max_iter=1000,
        C=0.1,
        class_weight="balanced",
        random_state=42,
    )

    # Champion Candidate Model: LightGBM
    lgb_estimator = LGBMClassifier(
        n_estimators=150,
        learning_rate=0.05,
        num_leaves=31,
        class_weight="balanced",
        random_state=42,
        verbosity=-1,
    )

    results = {}
    models = {
        "Logistic_Regression_Baseline": lr_estimator,
        "LightGBM_Candidate": lgb_estimator,
    }

    best_auc = -1.0
    best_pipeline = None
    best_name = ""

    for name, estimator in models.items():
        pipeline, metrics = train_single_model(
            name, estimator, X_train, y_train, X_val, y_val, preprocessor
        )
        results[name] = {"pipeline": pipeline, "metrics": metrics}

        if metrics["roc_auc"] > best_auc:
            best_auc = metrics["roc_auc"]
            best_pipeline = pipeline
            best_name = name

    # Persist best candidate model locally using dynamic path
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, CANDIDATE_MODEL_PATH)
    logger.info(f"Saved best model ({best_name} - AUC {best_auc:.4f}) to {CANDIDATE_MODEL_PATH}")

    return {
        "best_model_name": best_name,
        "best_auc": best_auc,
        "results": results,
    }


if __name__ == "__main__":
    run_training()
