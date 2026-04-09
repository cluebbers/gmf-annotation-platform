from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import AnnotationSource, GmfCategory


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(RequestSchema):
    title: str | None = None
    report_text: str
    source_url: str | None = None


class IncidentUpdate(RequestSchema):
    title: str | None = None
    report_text: str | None = None
    source_url: str | None = None

    @field_validator("report_text")
    @classmethod
    def validate_report_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("report_text may not be null")
        return value


class IncidentRead(ResponseSchema):
    id: int
    title: str | None
    report_text: str
    source_url: str | None
    created_at: datetime


class GoldAnnotationCreate(RequestSchema):
    gmf_category: GmfCategory
    label: str
    classification_discussion: str | None = None


class GoldAnnotationUpdate(RequestSchema):
    gmf_category: GmfCategory | None = None
    label: str | None = None
    classification_discussion: str | None = None

    @field_validator("gmf_category")
    @classmethod
    def validate_gmf_category(cls, value: GmfCategory | None) -> GmfCategory | None:
        if value is None:
            raise ValueError("gmf_category may not be null")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("label may not be null")
        return value


class GoldAnnotationRead(ResponseSchema):
    id: int
    incident_id: int
    source: AnnotationSource
    model_run_id: int | None
    gmf_category: GmfCategory
    label: str
    classification_discussion: str | None
    created_at: datetime


class SnippetCreate(RequestSchema):
    snippet_text: str
    snippet_order: int


class SnippetUpdate(RequestSchema):
    snippet_text: str | None = None
    snippet_order: int | None = None

    @field_validator("snippet_text")
    @classmethod
    def validate_snippet_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("snippet_text may not be null")
        return value

    @field_validator("snippet_order")
    @classmethod
    def validate_snippet_order(cls, value: int | None) -> int | None:
        if value is None:
            raise ValueError("snippet_order may not be null")
        return value


class SnippetRead(ResponseSchema):
    id: int
    annotation_id: int
    snippet_text: str
    snippet_order: int
    created_at: datetime


class DeleteResponse(BaseModel):
    status: Literal["deleted"]
