"""API routes for prediction functionality."""

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.ai_clients.google as google_client
import app.ai_clients.huggingface as hf_client
import app.ai_clients.openai as openai_client
from app.ai_clients.prompts import get_prompt
from app.api.schemas import (
    ModelRunRead,
    PredictResponse,
    PredictionLabels,
)
from app.config import settings
from app.db import get_db
from app.db.tables import (
    Annotation,
    AnnotationSource,
    GmfCategory,
    Incident,
    ModelRun,
    RunStatus,
)

router = APIRouter()


def _resolve_provider(model_name: str) -> str:
    if model_name.startswith("gemini"):
        return "google"
    if "/" in model_name:
        return "huggingface"
    return "openai"


@router.post("/predict/{incident_id}", response_model=PredictResponse)
def predict(
    incident_id: int,
    model_name: str | None = Query(default=None),
    prompt_version: str | None = Query(default=None),
    temperature: float | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PredictResponse:
    """Predict labels for an incident.

    Args:
        incident_id: The incident ID.
        model_name: Optional model name override.
        prompt_version: Optional prompt version override.
        temperature: Optional temperature override.
        db: Database session.

    Returns:
        Prediction response.

    Raises:
        HTTPException: If incident not found or API key not configured.
    """
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    effective_model = model_name or settings.openai_model
    provider = _resolve_provider(effective_model)

    if provider == "google" and not settings.google_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_API_KEY is not configured.",
        )
    if provider == "huggingface" and not settings.hf_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HF_TOKEN is not configured.",
        )
    if provider == "openai" and not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured.",
        )

    predict_fn = {
        "google": google_client.predict_incident,
        "huggingface": hf_client.predict_incident,
        "openai": openai_client.predict_incident,
    }[provider]

    if provider == "google":
        default_prompt_version = settings.google_prompt_version
    elif provider == "huggingface":
        default_prompt_version = settings.hf_prompt_version
    else:
        default_prompt_version = settings.openai_prompt_version

    effective_prompt_version = prompt_version or default_prompt_version
    system_prompt = get_prompt(effective_prompt_version)

    started_at = perf_counter()
    try:
        result = predict_fn(
            title=incident.title,
            report_text=incident.report_text,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    prediction = _normalize_prediction_labels(result)
    model_run = _save_successful_prediction(
        db=db,
        incident_id=incident.id,
        result=result,
        prediction=prediction,
        provider=provider,
        latency_ms=int((perf_counter() - started_at) * 1000),
        prompt_version=prompt_version,
        temperature=temperature,
    )

    return PredictResponse(
        incident_id=incident.id,
        model_run=ModelRunRead.model_validate(model_run),
        prediction=prediction,
    )


def _normalize_prediction_labels(result: dict[str, object]) -> PredictionLabels:
    """Normalize prediction labels from raw result.

    Args:
        result: Raw prediction result.

    Returns:
        Normalized prediction labels.
    """
    def normalize(values: object) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values if isinstance(values, list) else []:
            cleaned = str(value).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    return PredictionLabels(
        known_ai_technical_failure=normalize(
            result.get("known_ai_technical_failure")
        ),
        potential_ai_technical_failure=normalize(
            result.get("potential_ai_technical_failure")
        ),
    )


def _save_successful_prediction(
    db: Session,
    incident_id: int,
    result: dict[str, object],
    prediction: PredictionLabels,
    provider: str,
    latency_ms: int,
    prompt_version: str | None = None,
    temperature: float | None = None,
) -> ModelRun:
    """Save a successful prediction to the database.

    Args:
        db: Database session.
        incident_id: The incident ID.
        result: Raw prediction result.
        prediction: Normalized prediction labels.
        provider: Provider name ("openai", "google", "huggingface").
        latency_ms: Latency in milliseconds.
        prompt_version: Optional prompt version.
        temperature: Optional temperature.

    Returns:
        Created ModelRun.
    """
    if provider == "google":
        default_prompt_version = settings.google_prompt_version
        default_temperature = settings.google_temperature
        default_max_tokens = settings.google_max_output_tokens
    elif provider == "huggingface":
        default_prompt_version = settings.hf_prompt_version
        default_temperature = settings.hf_temperature
        default_max_tokens = settings.hf_max_tokens
    else:
        default_prompt_version = settings.openai_prompt_version
        default_temperature = settings.openai_temperature
        default_max_tokens = settings.openai_max_completion_tokens

    model_run = ModelRun(
        incident_id=incident_id,
        provider=provider,
        model_name=str(result["model_name"]),
        prompt_version=prompt_version or default_prompt_version,
        temperature=temperature if temperature is not None else default_temperature,
        max_completion_tokens=default_max_tokens,
        status=RunStatus.success,
        latency_ms=latency_ms,
        input_tokens=result["input_tokens"] if isinstance(result["input_tokens"], int) else None,
        output_tokens=result["output_tokens"] if isinstance(result["output_tokens"], int) else None,
        raw_response=str(result["raw_response"]),
    )

    try:
        db.add(model_run)
        db.flush()
        for category, labels in (
            (
                GmfCategory.known_ai_technical_failure,
                prediction.known_ai_technical_failure,
            ),
            (
                GmfCategory.potential_ai_technical_failure,
                prediction.potential_ai_technical_failure,
            ),
        ):
            for label in labels:
                db.add(
                    Annotation(
                        incident_id=incident_id,
                        source=AnnotationSource.prediction,
                        model_run_id=model_run.id,
                        gmf_category=category,
                        label=label,
                    )
                )
        db.commit()
        db.refresh(model_run)
        return model_run
    except SQLAlchemyError:
        db.rollback()
        raise
