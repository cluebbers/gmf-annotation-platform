"""Import AIID incidents and GMF technical-failure gold labels from backup archive."""

import argparse
import csv
import io
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import SessionLocal, init_db
from app.db.tables import (
    Annotation,
    AnnotationSource,
    GmfCategory,
    Incident,
    ModelRun,
)

DEFAULT_BACKUP_PATH = ROOT_DIR / "backup-20260330103116.tar.bz2"
INCIDENTS_MEMBER = "mongodump_full_snapshot/incidents.csv"
GMF_MEMBER = "mongodump_full_snapshot/classifications_GMF.csv"
TECHNICAL_FAILURE_COLUMNS = {
    GmfCategory.known_ai_technical_failure: "Known AI Technical Failure",
    GmfCategory.potential_ai_technical_failure: "Potential AI Technical Failure",
}


@dataclass(frozen=True)
class ImportStats:
    """Statistics from import operation."""
    incidents_created: int
    incidents_updated: int
    prediction_resets: int
    gold_incidents: int
    gold_annotations_created: int


@dataclass(frozen=True)
class ImportedIncident:
    """Incident data read from backup."""
    incident_id: int
    title: str | None
    report_text: str
    is_gold_set: bool


def main() -> None:
    """Main entry point for import script."""
    parser = argparse.ArgumentParser(
        description="Import AIID incidents and GMF technical-failure gold labels.",
    )
    parser.add_argument(
        "archive_path",
        nargs="?",
        default=str(DEFAULT_BACKUP_PATH),
        help="Path to the AIID backup tar.bz2 archive.",
    )
    args = parser.parse_args()

    archive_path = Path(args.archive_path).resolve()
    if not archive_path.exists():
        raise SystemExit(f"Archive not found: {archive_path}")

    stats = import_aiid_backup(archive_path)
    print(f"Imported archive: {archive_path}")
    print(f"Incidents created: {stats.incidents_created}")
    print(f"Incidents updated: {stats.incidents_updated}")
    print(f"Prediction resets: {stats.prediction_resets}")
    print(f"Gold incidents: {stats.gold_incidents}")
    print(f"Gold annotations created: {stats.gold_annotations_created}")


def import_aiid_backup(archive_path: Path) -> ImportStats:
    """Import incidents and labels from AIID backup archive.

    Args:
        archive_path: Path to backup tar.bz2 archive.

    Returns:
        Import statistics.
    """
    incidents = _load_incidents(archive_path)
    gold_labels_by_incident = _load_gold_labels(archive_path)

    init_db()

    incidents_created = 0
    incidents_updated = 0
    prediction_resets = 0
    gold_annotations_created = 0

    db = SessionLocal()
    try:
        for imported_incident in incidents:
            existing = db.get(Incident, imported_incident.incident_id)
            if existing is None:
                db.add(
                    Incident(
                        id=imported_incident.incident_id,
                        title=imported_incident.title,
                        report_text=imported_incident.report_text,
                        is_gold_set=imported_incident.is_gold_set,
                    )
                )
                incidents_created += 1
                continue

            incident_changed = (
                existing.title != imported_incident.title
                or existing.report_text != imported_incident.report_text
            )
            if incident_changed:
                _delete_prediction_data(db, imported_incident.incident_id)
                prediction_resets += 1

            existing.title = imported_incident.title
            existing.report_text = imported_incident.report_text
            existing.is_gold_set = imported_incident.is_gold_set
            incidents_updated += 1

        db.flush()

        for imported_incident in incidents:
            _delete_gold_annotations(db, imported_incident.incident_id)
            for category, labels in gold_labels_by_incident.get(
                imported_incident.incident_id, {}
            ).items():
                for label in labels:
                    db.add(
                        Annotation(
                            incident_id=imported_incident.incident_id,
                            source=AnnotationSource.gold,
                            model_run_id=None,
                            gmf_category=category,
                            label=label,
                        )
                    )
                    gold_annotations_created += 1

        db.flush()
        _sync_incident_id_sequence(db)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

    return ImportStats(
        incidents_created=incidents_created,
        incidents_updated=incidents_updated,
        prediction_resets=prediction_resets,
        gold_incidents=len(gold_labels_by_incident),
        gold_annotations_created=gold_annotations_created,
    )


def _load_incidents(archive_path: Path) -> list[ImportedIncident]:
    """Load incident data from archive.

    Args:
        archive_path: Path to backup archive.

    Returns:
        List of imported incidents.
    """
    incident_rows = _read_csv_from_tar(archive_path, INCIDENTS_MEMBER)
    gold_incident_ids = {
        int(row["Incident ID"])
        for row in _read_csv_from_tar(archive_path, GMF_MEMBER)
        if row.get("Incident ID")
    }

    incidents: list[ImportedIncident] = []
    for row in incident_rows:
        incident_id = int(row["incident_id"])
        incidents.append(
            ImportedIncident(
                incident_id=incident_id,
                title=_normalize_optional(row.get("title")),
                report_text=_normalize_required(
                    row.get("description"),
                    field_name=f"incidents.csv description for incident {incident_id}",
                ),
                is_gold_set=incident_id in gold_incident_ids,
            )
        )
    return incidents


def _load_gold_labels(
    archive_path: Path,
) -> dict[int, dict[GmfCategory, list[str]]]:
    """Load gold label annotations from archive.

    Args:
        archive_path: Path to backup archive.

    Returns:
        Dictionary mapping incident IDs to label categories and labels.
    """
    labels_by_incident: dict[int, dict[GmfCategory, list[str]]] = {}
    for row in _read_csv_from_tar(archive_path, GMF_MEMBER):
        incident_id = int(row["Incident ID"])
        labels_by_incident[incident_id] = {
            category: _split_label_field(row.get(column_name))
            for category, column_name in TECHNICAL_FAILURE_COLUMNS.items()
        }
    return labels_by_incident


def _delete_gold_annotations(db: Session, incident_id: int) -> None:
    """Delete all gold annotations for an incident.

    Args:
        db: Database session.
        incident_id: The incident ID.
    """
    db.execute(
        delete(Annotation).where(
            Annotation.incident_id == incident_id,
            Annotation.source == AnnotationSource.gold,
        )
    )
    db.flush()


def _delete_prediction_data(db: Session, incident_id: int) -> None:
    """Delete all prediction data for an incident.

    Args:
        db: Database session.
        incident_id: The incident ID.
    """
    db.execute(
        delete(Annotation).where(
            Annotation.incident_id == incident_id,
            Annotation.source == AnnotationSource.prediction,
        )
    )
    db.execute(delete(ModelRun).where(ModelRun.incident_id == incident_id))
    db.flush()


def _read_csv_from_tar(archive_path: Path, member_name: str) -> list[dict[str, str]]:
    """Read CSV file from tar.bz2 archive.

    Args:
        archive_path: Path to archive.
        member_name: Name of member in archive.

    Returns:
        List of CSV rows as dictionaries.
    """
    with tarfile.open(archive_path, "r:bz2") as tar:
        file_obj = tar.extractfile(member_name)
        if file_obj is None:
            raise FileNotFoundError(f"Archive member not found: {member_name}")
        raw = file_obj.read().decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(raw)))


def _split_label_field(value: str | None) -> list[str]:
    """Split comma-separated labels and normalize.

    Args:
        value: Comma-separated label string.

    Returns:
        List of normalized labels.
    """
    if value is None:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for label in value.split(","):
        cleaned = label.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    """Normalize optional string value.

    Args:
        value: Input value.

    Returns:
        Normalized value or None.
    """
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _normalize_required(value: str | None, field_name: str) -> str:
    """Normalize required string value.

    Args:
        value: Input value.
        field_name: Field name for error message.

    Returns:
        Normalized value.

    Raises:
        ValueError: If value is empty.
    """
    normalized = _normalize_optional(value)
    if normalized is None:
        raise ValueError(f"Missing required value for {field_name}")
    return normalized


def _sync_incident_id_sequence(db: Session) -> None:
    """Sync PostgreSQL sequence for incident ID generation.

    Args:
        db: Database session.
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    db.execute(
        text(
            "SELECT setval("
            "pg_get_serial_sequence('incidents', 'id'), "
            "COALESCE((SELECT MAX(id) FROM incidents), 1), "
            "true"
            ")"
        )
    )


if __name__ == "__main__":
    main()
