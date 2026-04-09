from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.schemas import (
    DeleteResponse,
    GoldAnnotationCreate,
    GoldAnnotationRead,
    GoldAnnotationUpdate,
)
from app.db import get_db
from app.models import Annotation, AnnotationSnippet, AnnotationSource, Incident

router = APIRouter(tags=["gold annotations"])


def get_gold_annotation_or_404(db: Session, annotation_id: int) -> Annotation:
    statement = select(Annotation).where(
        Annotation.id == annotation_id,
        Annotation.source == AnnotationSource.gold,
    )
    annotation = db.execute(statement).scalar_one_or_none()
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gold annotation not found.",
        )

    return annotation


@router.get(
    "/incidents/{incident_id}/gold-annotations",
    response_model=list[GoldAnnotationRead],
)
def list_gold_annotations(
    incident_id: int,
    db: Session = Depends(get_db),
) -> list[Annotation]:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    statement = select(Annotation).where(
        Annotation.incident_id == incident_id,
        Annotation.source == AnnotationSource.gold,
    ).order_by(Annotation.id.desc())
    return db.execute(statement).scalars().all()


@router.post(
    "/incidents/{incident_id}/gold-annotations",
    response_model=GoldAnnotationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_gold_annotation(
    incident_id: int,
    payload: GoldAnnotationCreate,
    db: Session = Depends(get_db),
) -> Annotation:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    annotation = Annotation(
        incident_id=incident.id,
        source=AnnotationSource.gold,
        model_run_id=None,
        gmf_category=payload.gmf_category,
        label=payload.label,
        classification_discussion=payload.classification_discussion,
    )

    try:
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
    except SQLAlchemyError:
        db.rollback()
        raise

    return annotation


@router.get("/gold-annotations/{annotation_id}", response_model=GoldAnnotationRead)
def get_gold_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
) -> Annotation:
    return get_gold_annotation_or_404(db, annotation_id)


@router.put("/gold-annotations/{annotation_id}", response_model=GoldAnnotationRead)
def update_gold_annotation(
    annotation_id: int,
    payload: GoldAnnotationUpdate,
    db: Session = Depends(get_db),
) -> Annotation:
    annotation = get_gold_annotation_or_404(db, annotation_id)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    for field, value in updates.items():
        setattr(annotation, field, value)

    try:
        db.commit()
        db.refresh(annotation)
    except SQLAlchemyError:
        db.rollback()
        raise

    return annotation


@router.delete("/gold-annotations/{annotation_id}", response_model=DeleteResponse)
def delete_gold_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    annotation = get_gold_annotation_or_404(db, annotation_id)

    snippets = db.execute(
        select(AnnotationSnippet).where(AnnotationSnippet.annotation_id == annotation.id)
    ).scalars().all()

    try:
        for snippet in snippets:
            db.delete(snippet)
        db.flush()

        db.delete(annotation)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return DeleteResponse(status="deleted")
