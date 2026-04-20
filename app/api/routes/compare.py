"""API routes for model comparison."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import CategoryMetrics, CompareResponse
from app.db import get_db
from app.db.tables import Annotation, AnnotationSource, GmfCategory, Incident, ModelRun, RunStatus

router = APIRouter()

ALLOWED_MODELS = ["gpt-4o-mini", "gpt-5-mini"]


class CompareConfigsResponse(BaseModel):
    """Schema for available comparison configurations."""
    models: list[str]
    prompt_versions: list[str]
    temperatures: list[float]


@router.get("/compare/configs", response_model=CompareConfigsResponse)
def compare_configs(db: Session = Depends(get_db)) -> CompareConfigsResponse:
    """Get available comparison configurations.

    Args:
        db: Database session.

    Returns:
        Available models, prompt versions, and temperatures.
    """
    prompt_versions = db.execute(
        select(ModelRun.prompt_version).distinct().order_by(ModelRun.prompt_version.asc())
    ).scalars().all()
    temperatures = db.execute(
        select(ModelRun.temperature).distinct().where(ModelRun.temperature.isnot(None)).order_by(ModelRun.temperature.asc())
    ).scalars().all()
    return CompareConfigsResponse(
        models=ALLOWED_MODELS,
        prompt_versions=list(prompt_versions),
        temperatures=list(temperatures),
    )


def _label_sets(
    db: Session,
    incident_id: int,
    source: AnnotationSource,
    model_run_id: int | None = None,
) -> dict[GmfCategory, set[str]]:
    """Get label sets for an incident.

    Args:
        db: Database session.
        incident_id: The incident ID.
        source: The annotation source.
        model_run_id: Optional model run ID to filter.

    Returns:
        Dictionary mapping categories to sets of labels.
    """
    stmt = select(Annotation.gmf_category, Annotation.label).where(
        Annotation.incident_id == incident_id,
        Annotation.source == source,
    )
    if model_run_id is not None:
        stmt = stmt.where(Annotation.model_run_id == model_run_id)
    result: dict[GmfCategory, set[str]] = {
        GmfCategory.known_ai_technical_failure: set(),
        GmfCategory.potential_ai_technical_failure: set(),
    }
    for category, label in db.execute(stmt):
        result[category].add(label.strip())
    return result


def _metrics(tp: int, fp: int, fn: int) -> CategoryMetrics:
    """Calculate precision, recall, and F1 score.

    Args:
        tp: True positives.
        fp: False positives.
        fn: False negatives.

    Returns:
        Category metrics.
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0
    return CategoryMetrics(precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4))


@router.get("/compare", response_model=CompareResponse)
def compare(
    model_name: str = Query(...),
    prompt_version: str = Query(...),
    temperature: float | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CompareResponse:
    """Compare model performance across configurations.

    Args:
        model_name: The model name to compare.
        prompt_version: The prompt version.
        temperature: Optional temperature filter.
        db: Database session.

    Returns:
        Comparison results including metrics.
    """
    gold_incidents = db.execute(
        select(Incident.id).where(Incident.is_gold_set.is_(True))
    ).scalars().all()

    totals: dict[GmfCategory, dict[str, int]] = {
        GmfCategory.known_ai_technical_failure: {"tp": 0, "fp": 0, "fn": 0},
        GmfCategory.potential_ai_technical_failure: {"tp": 0, "fp": 0, "fn": 0},
    }
    covered = 0
    total_input_tokens = 0
    total_output_tokens = 0
    token_count = 0

    for incident_id in gold_incidents:
        stmt = (
            select(ModelRun)
            .where(
                ModelRun.incident_id == incident_id,
                ModelRun.model_name == model_name,
                ModelRun.prompt_version == prompt_version,
                ModelRun.status == RunStatus.success,
            )
        )
        if temperature is not None:
            stmt = stmt.where(ModelRun.temperature == temperature)
        run = db.execute(stmt.order_by(ModelRun.created_at.desc()).limit(1)).scalar_one_or_none()

        if run is None:
            continue

        covered += 1
        if run.input_tokens is not None and run.output_tokens is not None:
            total_input_tokens += run.input_tokens
            total_output_tokens += run.output_tokens
            token_count += 1

        gold = _label_sets(db, incident_id, AnnotationSource.gold)
        pred = _label_sets(db, incident_id, AnnotationSource.prediction, model_run_id=run.id)

        for category in totals:
            g = gold[category]
            p = pred[category]
            totals[category]["tp"] += len(g & p)
            totals[category]["fp"] += len(p - g)
            totals[category]["fn"] += len(g - p)

    return CompareResponse(
        model_name=model_name,
        prompt_version=prompt_version,
        temperature=temperature,
        gold_incident_count=len(gold_incidents),
        covered_incident_count=covered,
        avg_input_tokens=round(total_input_tokens / token_count, 1) if token_count else None,
        avg_output_tokens=round(total_output_tokens / token_count, 1) if token_count else None,
        known_ai_technical_failure=_metrics(**totals[GmfCategory.known_ai_technical_failure]),
        potential_ai_technical_failure=_metrics(**totals[GmfCategory.potential_ai_technical_failure]),
    )
