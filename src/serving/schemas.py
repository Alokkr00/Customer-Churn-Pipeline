"""Pydantic request and response schemas for model serving API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerInput(BaseModel):
    """Customer attributes payload for real-time churn prediction."""

    customer_id: Optional[str] = Field(default="CUST-PRED-001", description="Customer identifier")
    gender: Optional[str] = Field(default="Female", description="Gender: Male, Female")
    senior_citizen: Optional[int] = Field(default=0, ge=0, le=1, description="1 if senior, else 0")
    partner: Optional[str] = Field(default="No", description="Yes or No")
    dependents: Optional[str] = Field(default="No", description="Yes or No")
    tenure_months: int = Field(default=6, ge=0, le=120, description="Months with company")
    phone_service: Optional[str] = Field(default="Yes", description="Yes or No")
    multiple_lines: Optional[str] = Field(default="No", description="Yes, No, No phone service")
    internet_service: str = Field(default="Fiber optic", description="DSL, Fiber optic, No")
    online_security: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    online_backup: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    device_protection: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    tech_support: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    streaming_tv: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    streaming_movies: Optional[str] = Field(default="No", description="Yes, No, No internet service")
    contract_type: str = Field(default="Month-to-month", description="Month-to-month, One year, Two year")
    paperless_billing: Optional[str] = Field(default="Yes", description="Yes or No")
    payment_method: str = Field(
        default="Electronic check",
        description="Electronic check, Mailed check, Bank transfer (automatic), Credit card (automatic)",
    )
    monthly_charges: float = Field(default=79.50, ge=0.0, description="Monthly charges in USD")
    total_charges: Optional[float] = Field(default=477.00, ge=0.0, description="Total charges to date in USD")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "CUST-9821-HIGH",
                "gender": "Female",
                "senior_citizen": 0,
                "partner": "No",
                "dependents": "No",
                "tenure_months": 3,
                "phone_service": "Yes",
                "multiple_lines": "No",
                "internet_service": "Fiber optic",
                "online_security": "No",
                "online_backup": "No",
                "device_protection": "No",
                "tech_support": "No",
                "streaming_tv": "Yes",
                "streaming_movies": "Yes",
                "contract_type": "Month-to-month",
                "paperless_billing": "Yes",
                "payment_method": "Electronic check",
                "monthly_charges": 89.20,
                "total_charges": 267.60,
            }
        }
    )


class PredictionResponse(BaseModel):
    """Prediction output containing risk score, tier, and actionable recommendations."""

    customer_id: str
    churn_probability: float
    churn_prediction: int
    risk_tier: str
    top_risk_drivers: List[str]
    recommended_retention_action: str
    model_version: str
    latency_ms: float


class BatchPredictionRequest(BaseModel):
    """Batch prediction payload."""

    customers: List[CustomerInput]


class BatchPredictionResponse(BaseModel):
    """Batch prediction output."""

    total_customers: int
    predictions: List[PredictionResponse]


class HighRiskCustomer(BaseModel):
    """Schema for individual customer in the high-risk cohort."""

    customer_id: str
    churn_probability: float
    risk_tier: str
    top_reasons: List[str]
    monthly_charges: float
    contract_type: str
    scored_at: Optional[str] = None


class HighRiskResponse(BaseModel):
    """Response containing high-risk customer list."""

    total_high_risk: int
    threshold: float
    customers: List[HighRiskCustomer]


class ModelInfoResponse(BaseModel):
    """Current production model metadata and health."""

    model_name: str
    model_version: str
    model_type: str
    is_loaded: bool
    status: str
    last_updated: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
