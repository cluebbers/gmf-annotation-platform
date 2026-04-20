from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai_clients.openai import predict_incident
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


@router.post("/predict/{incident_id}", response_model=PredictResponse)
def predict(
    incident_id: int,
    model_name: str | None = Query(default=None),
    prompt_version: str | None = Query(default=None),
    temperature: float | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PredictResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured.",
        )

    started_at = perf_counter()
    try:
        result = predict_incident(
            title=incident.title,
            report_text=incident.report_text,
            model_name=model_name,
            temperature=temperature,
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
    latency_ms: int,
    prompt_version: str | None = None,
    temperature: float | None = None,
) -> ModelRun:
    model_run = ModelRun(
        incident_id=incident_id,
        provider="openai",
        model_name=str(result["model_name"]),
        prompt_version=prompt_version or settings.openai_prompt_version,
        temperature=temperature if temperature is not None else settings.openai_temperature,
        max_completion_tokens=settings.openai_max_completion_tokens,
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
