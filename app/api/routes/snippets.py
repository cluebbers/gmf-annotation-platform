from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.schemas import DeleteResponse, SnippetCreate, SnippetRead, SnippetUpdate
from app.db import get_db
from app.models import Annotation, AnnotationSnippet

router = APIRouter(tags=["snippets"])


def get_annotation_or_404(db: Session, annotation_id: int) -> Annotation:
    annotation = db.get(Annotation, annotation_id)
    if annotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")

    return annotation


def get_snippet_or_404(db: Session, snippet_id: int) -> AnnotationSnippet:
    snippet = db.get(AnnotationSnippet, snippet_id)
    if snippet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found.")

    return snippet


@router.get("/annotations/{annotation_id}/snippets", response_model=list[SnippetRead])
def list_snippets(
    annotation_id: int,
    db: Session = Depends(get_db),
) -> list[AnnotationSnippet]:
    get_annotation_or_404(db, annotation_id)

    statement = select(AnnotationSnippet).where(
        AnnotationSnippet.annotation_id == annotation_id
    ).order_by(AnnotationSnippet.snippet_order.asc(), AnnotationSnippet.id.asc())
    return db.execute(statement).scalars().all()


@router.post(
    "/annotations/{annotation_id}/snippets",
    response_model=SnippetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_snippet(
    annotation_id: int,
    payload: SnippetCreate,
    db: Session = Depends(get_db),
) -> AnnotationSnippet:
    get_annotation_or_404(db, annotation_id)

    snippet = AnnotationSnippet(
        annotation_id=annotation_id,
        snippet_text=payload.snippet_text,
        snippet_order=payload.snippet_order,
    )

    try:
        db.add(snippet)
        db.commit()
        db.refresh(snippet)
    except SQLAlchemyError:
        db.rollback()
        raise

    return snippet


@router.put("/snippets/{snippet_id}", response_model=SnippetRead)
def update_snippet(
    snippet_id: int,
    payload: SnippetUpdate,
    db: Session = Depends(get_db),
) -> AnnotationSnippet:
    snippet = get_snippet_or_404(db, snippet_id)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    for field, value in updates.items():
        setattr(snippet, field, value)

    try:
        db.commit()
        db.refresh(snippet)
    except SQLAlchemyError:
        db.rollback()
        raise

    return snippet


@router.delete("/snippets/{snippet_id}", response_model=DeleteResponse)
def delete_snippet(
    snippet_id: int,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    snippet = get_snippet_or_404(db, snippet_id)

    try:
        db.delete(snippet)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return DeleteResponse(status="deleted")
