"""FastAPI Model Serving Application.

Provides production-ready REST endpoints for:
- Real-time customer churn prediction with explainable risk drivers
- Batch customer scoring
- High-risk customer cohort retrieval for retention teams
- Active model metadata and health checks
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine, text

from src.data.ingest import get_db_url
from src.data.preprocess import preprocess_features
from src.features.feature_engineering import filter_available_features
from src.scoring.score import (
    HIGH_RISK_THRESHOLD,
    assign_risk_tier,
    extract_top_risk_drivers,
    load_scoring_model,
)
from src.serving.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    CustomerInput,
    HighRiskCustomer,
    HighRiskResponse,
    ModelInfoResponse,
    PredictionResponse,
)
from src.utils.paths import (
    REPORTS_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global model cache state
model_state: Dict[str, Any] = {
    "model": None,
    "version": "unloaded",
    "loaded_at": None,
    "model_type": "None",
}


def get_recommended_action(risk_tier: str, drivers: List[str], row_data: Dict[str, Any]) -> str:
    """Determine prioritized retention campaign action based on risk drivers."""
    if risk_tier == "Low":
        return "No intervention required. Eligible for premium add-on upsell."

    contract = str(row_data.get("contract_type", ""))
    payment = str(row_data.get("payment_method", ""))
    has_tech = int(row_data.get("has_tech_support", 0))

    if "Month-to-month" in contract:
        return "Offer 15% discount for 1-year contract lock-in."
    if payment == "Electronic check":
        return "Incentivize automatic payment enrollment with a $10 bill credit."
    if not has_tech:
        return "Bundle 3 months of complimentary 24/7 Tech Support."

    return "Assign to Senior Retention Specialist for high-touch proactive outreach."


def load_model_into_state() -> None:
    """Load model from canonical storage into global state."""
    try:
        model, version = load_scoring_model()
        model_state["model"] = model
        model_state["version"] = version
        model_state["loaded_at"] = datetime.now(timezone.utc).isoformat()
        if hasattr(model, "named_steps"):
            classifier_step = model.named_steps.get("classifier", None)
            model_state["model_type"] = (
                classifier_step.__class__.__name__ if classifier_step else "Pipeline"
            )
        else:
            model_state["model_type"] = model.__class__.__name__
        logger.info(f"Loaded {model_state['model_type']} ({version}) into memory.")
    except Exception as exc:
        logger.warning(f"Could not preload model during startup: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and teardown."""
    load_model_into_state()
    yield
    model_state["model"] = None


app = FastAPI(
    title="Customer Churn Prediction & Retention API",
    description=(
        "Production MLOps inference service powering real-time churn prediction, "
        "explainable risk driver diagnostics, and retention campaign targeting."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Check service health and model readiness probe."""
    is_ready = model_state["model"] is not None
    return {
        "status": "healthy" if is_ready else "degraded",
        "model_loaded": is_ready,
        "model_version": model_state["version"],
        "model_type": model_state["model_type"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/model-info", response_model=ModelInfoResponse, tags=["Model Governance"])
def get_model_info() -> ModelInfoResponse:
    """Retrieve details, hyperparameters, and status of active production model."""
    if model_state["model"] is None:
        load_model_into_state()

    is_loaded = model_state["model"] is not None
    params = {}
    if is_loaded:
        model_obj = model_state["model"]
        if hasattr(model_obj, "named_steps"):
            clf = model_obj.named_steps.get("classifier", model_obj)
        else:
            clf = model_obj

        if clf and hasattr(clf, "get_params"):
            params = {k: str(v) for k, v in clf.get_params().items() if not k.startswith("_")}

    return ModelInfoResponse(
        model_name="customer_churn_classifier",
        model_version=model_state["version"],
        model_type=model_state["model_type"],
        is_loaded=is_loaded,
        status="active" if is_loaded else "unloaded",
        last_updated=model_state["loaded_at"],
        parameters=params,
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_churn(customer: CustomerInput) -> PredictionResponse:
    """Generate real-time churn probability, risk tier, and retention recommendation."""
    start_time = time.perf_counter()

    if model_state["model"] is None:
        load_model_into_state()
        if model_state["model"] is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not loaded. Train a model with 'make train' first.",
            )

    model: Pipeline = model_state["model"]

    # Convert customer payload to DataFrame
    customer_dict = customer.model_dump()
    raw_df = pd.DataFrame([customer_dict])

    # Run standard preprocessing
    proc_df = preprocess_features(raw_df)

    num_cols, cat_cols, bin_cols = filter_available_features(proc_df)
    feature_cols = num_cols + cat_cols + bin_cols

    X = proc_df[feature_cols]

    # Predict probability
    proba = float(model.predict_proba(X)[0, 1])
    pred_label = int(proba >= 0.5)
    risk_tier = assign_risk_tier(proba)
    drivers = extract_top_risk_drivers(proc_df.iloc[0])
    recommendation = get_recommended_action(risk_tier, drivers, proc_df.iloc[0].to_dict())

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return PredictionResponse(
        customer_id=customer.customer_id or "UNKNOWN",
        churn_probability=round(proba, 4),
        churn_prediction=pred_label,
        risk_tier=risk_tier,
        top_risk_drivers=drivers,
        recommended_retention_action=recommendation,
        model_version=model_state["version"],
        latency_ms=latency_ms,
    )


@app.post("/predict-batch", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_churn_batch(batch: BatchPredictionRequest) -> BatchPredictionResponse:
    """Score a batch of customer records synchronously."""
    predictions = [predict_churn(c) for c in batch.customers]
    return BatchPredictionResponse(
        total_customers=len(predictions),
        predictions=predictions,
    )


@app.get("/high-risk", response_model=HighRiskResponse, tags=["Retention Cohorts"])
def get_high_risk_customers(
    threshold: float = Query(
        default=HIGH_RISK_THRESHOLD, ge=0.0, le=1.0, description="Minimum churn probability"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum customers to return"),
) -> HighRiskResponse:
    """Query high-risk customers requiring immediate retention intervention."""
    customers_list: List[HighRiskCustomer] = []

    # Priority 1: Query PostgreSQL scoring schema
    try:
        engine = create_engine(get_db_url())
        query = text(
            """
            SELECT customer_id, churn_probability, risk_tier, top_reasons, scored_at
            FROM scoring.churn_scores
            WHERE churn_probability >= :thresh
            ORDER BY churn_probability DESC
            LIMIT :lim
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"thresh": threshold, "lim": limit}).fetchall()
            for r in rows:
                reasons = []
                try:
                    reasons = json.loads(r.top_reasons) if r.top_reasons else []
                except Exception:
                    reasons = [str(r.top_reasons)]

                customers_list.append(
                    HighRiskCustomer(
                        customer_id=str(r.customer_id),
                        churn_probability=float(r.churn_probability),
                        risk_tier=str(r.risk_tier),
                        top_reasons=reasons,
                        monthly_charges=0.0,
                        contract_type="Month-to-month",
                        scored_at=str(r.scored_at),
                    )
                )
    except Exception as exc:
        logger.info(f"Database query skipped ({exc}). Checking fallback report...")

    # Priority 2: Fallback to local exported CSV if DB returned no records
    if not customers_list:
        csv_path = REPORTS_DIR / "high_risk_customers.csv"
        if csv_path.exists():
            df_csv = pd.read_csv(csv_path)
            filtered = df_csv[df_csv["churn_probability"] >= threshold].head(limit)
            for _, row in filtered.iterrows():
                reasons = []
                raw_reasons = row.get("top_reasons", "[]")
                try:
                    reasons = json.loads(raw_reasons)
                except Exception:
                    reasons = [str(raw_reasons)]

                customers_list.append(
                    HighRiskCustomer(
                        customer_id=str(row["customer_id"]),
                        churn_probability=float(row["churn_probability"]),
                        risk_tier=str(row["risk_tier"]),
                        top_reasons=reasons,
                        monthly_charges=float(row.get("monthly_charges", 0.0)),
                        contract_type=str(row.get("contract_type", "Month-to-month")),
                        scored_at=str(row.get("scored_at", "")),
                    )
                )

    return HighRiskResponse(
        total_high_risk=len(customers_list),
        threshold=threshold,
        customers=customers_list,
    )
