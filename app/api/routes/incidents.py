from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import IncidentDetailRead, IncidentRead, PredictionLabels
from app.db import get_db
from app.db.tables import Annotation, AnnotationSource, GmfCategory, Incident

router = APIRouter()


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    statement = select(Incident).order_by(Incident.id.asc())
    return db.execute(statement).scalars().all()


@router.get("/incidents/{incident_id}", response_model=IncidentDetailRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> IncidentDetailRead:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )
    return IncidentDetailRead(
        id=incident.id,
        title=incident.title,
        report_text=incident.report_text,
        is_gold_set=incident.is_gold_set,
        created_at=incident.created_at,
        gold_annotations=_load_gold_annotations(db, incident.id)
        if incident.is_gold_set
        else None,
    )


def _load_gold_annotations(db: Session, incident_id: int) -> PredictionLabels:
    labels_by_category = {
        GmfCategory.known_ai_technical_failure: [],
        GmfCategory.potential_ai_technical_failure: [],
    }
    seen_by_category = {
        GmfCategory.known_ai_technical_failure: set(),
        GmfCategory.potential_ai_technical_failure: set(),
    }
    statement = (
        select(Annotation.gmf_category, Annotation.label)
        .where(
            Annotation.incident_id == incident_id,
            Annotation.source == AnnotationSource.gold,
        )
        .order_by(Annotation.id.asc())
    )

    for category, label in db.execute(statement):
        cleaned = label.strip()
        if not cleaned or cleaned in seen_by_category[category]:
            continue
        seen_by_category[category].add(cleaned)
        labels_by_category[category].append(cleaned)

    return PredictionLabels(
        known_ai_technical_failure=labels_by_category[
            GmfCategory.known_ai_technical_failure
        ],
        potential_ai_technical_failure=labels_by_category[
            GmfCategory.potential_ai_technical_failure
        ],
    )
