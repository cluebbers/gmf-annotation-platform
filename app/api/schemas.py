"""Pydantic schemas for API request/response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.tables import RunStatus


class ResponseSchema(BaseModel):
    """Base schema with configuration for response models."""
    model_config = ConfigDict(from_attributes=True)


class IncidentRead(ResponseSchema):
    """Schema for reading incident data."""
    id: int
    title: str | None
    report_text: str
    is_gold_set: bool
    created_at: datetime


class ModelRunRead(ResponseSchema):
    """Schema for reading model run data."""
    id: int
    incident_id: int
    provider: str
    model_name: str
    prompt_version: str
    temperature: float | None
    max_completion_tokens: int | None
    status: RunStatus
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime


class PredictionLabels(BaseModel):
    """Schema for prediction labels."""
    known_ai_technical_failure: list[str] = Field(default_factory=list)
    potential_ai_technical_failure: list[str] = Field(default_factory=list)


class IncidentDetailRead(IncidentRead):
    """Schema for detailed incident data including gold annotations."""
    gold_annotations: PredictionLabels | None = None


class PredictResponse(BaseModel):
    """Schema for prediction response."""
    incident_id: int
    model_run: ModelRunRead
    prediction: PredictionLabels


class CategoryMetrics(BaseModel):
    """Schema for category metrics."""
    precision: float
    recall: float
    f1: float


class CompareResponse(BaseModel):
    """Schema for comparison response."""
    model_name: str
    prompt_version: str
    temperature: float | None
    gold_incident_count: int
    covered_incident_count: int
    avg_input_tokens: float | None
    avg_output_tokens: float | None
    known_ai_technical_failure: CategoryMetrics
    potential_ai_technical_failure: CategoryMetrics
