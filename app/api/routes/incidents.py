from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.schemas import DeleteResponse, IncidentCreate, IncidentRead, IncidentUpdate
from app.db import get_db
from app.models import Annotation, AnnotationSnippet, Incident, ModelRun

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    statement = select(Incident).order_by(Incident.id.desc())
    return db.execute(statement).scalars().all()


@router.post(
    "/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
) -> Incident:
    incident = Incident(
        title=payload.title,
        report_text=payload.report_text,
        source_url=payload.source_url,
    )

    try:
        db.add(incident)
        db.commit()
        db.refresh(incident)
    except SQLAlchemyError:
        db.rollback()
        raise

    return incident


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    return incident


@router.put("/incidents/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    for field, value in updates.items():
        setattr(incident, field, value)

    try:
        db.commit()
        db.refresh(incident)
    except SQLAlchemyError:
        db.rollback()
        raise

    return incident


@router.delete("/incidents/{incident_id}", response_model=DeleteResponse)
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    annotation_ids = db.execute(
        select(Annotation.id).where(Annotation.incident_id == incident.id)
    ).scalars().all()

    if annotation_ids:
        snippets = db.execute(
            select(AnnotationSnippet).where(
                AnnotationSnippet.annotation_id.in_(annotation_ids)
            )
        ).scalars().all()
        for snippet in snippets:
            db.delete(snippet)

    annotations = db.execute(
        select(Annotation).where(Annotation.incident_id == incident.id)
    ).scalars().all()
    model_runs = db.execute(
        select(ModelRun).where(ModelRun.incident_id == incident.id)
    ).scalars().all()

    try:
        db.flush()

        for annotation in annotations:
            db.delete(annotation)
        db.flush()

        for model_run in model_runs:
            db.delete(model_run)
        db.flush()

        db.delete(incident)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return DeleteResponse(status="deleted")
