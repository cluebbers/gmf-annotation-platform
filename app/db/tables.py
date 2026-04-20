"""Database table definitions using SQLAlchemy ORM."""

import enum
from datetime import datetime

from app.db import Base
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
    func,
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column


class RunStatus(str, enum.Enum):
    """Enumeration of possible model run statuses."""
    success = "success"
    failed = "failed"


class AnnotationSource(str, enum.Enum):
    """Enumeration of annotation sources."""
    gold = "gold"
    prediction = "prediction"


class GmfCategory(str, enum.Enum):
    """Enumeration of GMF categories."""
    known_ai_technical_failure = "known_ai_technical_failure"
    potential_ai_technical_failure = "potential_ai_technical_failure"


class Incident(Base):
    """Represents an incident in the database."""
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_gold_set: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ModelRun(Base):
    """Represents a model run in the database."""
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    provider: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="openai",
        server_default=sql_text("'openai'"),
    )
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False),
        nullable=False,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Annotation(Base):
    """Represents an annotation in the database."""
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    source: Mapped[AnnotationSource] = mapped_column(
        Enum(AnnotationSource, native_enum=False),
        nullable=False,
    )
    model_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_runs.id"),
        nullable=True,
    )
    gmf_category: Mapped[GmfCategory] = mapped_column(
        Enum(GmfCategory, native_enum=False),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
