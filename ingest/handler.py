from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID

import psycopg

from ingest import db
from ingest.validation import CleanRow, check_columns, validate_row

logger = logging.getLogger(__name__)


@dataclass
class FileReport:
    batch_id: UUID | None
    source_filename: str
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    error: str | None = None
    rejections: list[tuple[int, str]] = field(default_factory=list)


def parse_and_validate(
    source: TextIO,
) -> tuple[list[tuple[int, dict]], list[tuple[int, CleanRow]], list[tuple[int, dict, str]]]:
    reader = csv.DictReader(source)
    column_error = check_columns(reader.fieldnames)
    if column_error:
        raise ValueError(column_error)

    staging: list[tuple[int, dict]] = []
    clean: list[tuple[int, CleanRow]] = []
    rejected: list[tuple[int, dict, str]] = []
    first_seen: dict[str, int] = {}

    for row_number, raw in enumerate(reader, start=2):  
        if None in raw or any(value is None for value in raw.values()):
            rejected.append((row_number, dict(raw), "column count mismatch"))
            continue
        raw = {(key or "").strip().lower(): value for key, value in raw.items()}
        staging.append((row_number, raw))

        row, reason = validate_row(raw)
        if row is None:
            rejected.append((row_number, raw, reason or "unknown validation error"))
            continue
        if row.user_id in first_seen:
            rejected.append(
                (
                    row_number,
                    raw,
                    f"duplicate user_id in file; first occurrence at row "
                    f"{first_seen[row.user_id]} kept",
                )
            )
            continue
        first_seen[row.user_id] = row_number
        clean.append((row_number, row))

    return staging, clean, rejected


def process_file(
    source: str | Path | TextIO,
    source_filename: str | None = None,
    conn: psycopg.Connection | None = None,
) -> FileReport:
    """Ingest one CSV file. With `conn` given the caller owns the transaction."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        name = source_filename or path.name
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return _process(handle, name, conn)
    return _process(source, source_filename or "stream", conn)


def _create_failed_batch(
    active_conn: psycopg.Connection, source_filename: str, error: str
) -> UUID:
    """Record a file-level failure in the audit trail (batch with 0 rows)."""
    batch_id = db.create_batch(active_conn, source_filename)
    db.finish_batch(active_conn, batch_id, 0, 0, 0, status="failed", error=error)
    return batch_id


def _process(
    handle: TextIO, source_filename: str, conn: psycopg.Connection | None
) -> FileReport:
    report = FileReport(batch_id=None, source_filename=source_filename)
    try:
        staging, clean, rejected = parse_and_validate(handle)
    except ValueError as exc:
        error = str(exc)
        report.error = error
        logger.error("%s: %s", source_filename, error)
        if conn is None:
            with db.connect() as own_conn:
                report.batch_id = _create_failed_batch(own_conn, source_filename, error)
        else:
            report.batch_id = _create_failed_batch(conn, source_filename, error)
        return report

    report.total_rows = len(staging)
    report.valid_rows = len(clean)
    report.rejected_rows = len(rejected)
    report.rejections = [(number, reason) for number, _raw, reason in rejected]

    if conn is None:
        with db.connect() as own_conn:
            report.batch_id = _load(own_conn, report, staging, clean, rejected)
    else:
        report.batch_id = _load(conn, report, staging, clean, rejected)

    logger.info(
        "%s: batch=%s total=%d valid=%d rejected=%d",
        source_filename,
        report.batch_id,
        report.total_rows,
        report.valid_rows,
        report.rejected_rows,
    )
    return report


def _load(
    conn: psycopg.Connection,
    report: FileReport,
    staging: list[tuple[int, dict]],
    clean: list[tuple[int, CleanRow]],
    rejected: list[tuple[int, dict, str]],
) -> UUID:
    batch_id = db.create_batch(conn, report.source_filename)
    db.record_staging(conn, batch_id, [(n, raw) for n, raw in staging])
    db.record_rejected(conn, batch_id, rejected)
    db.upsert_users(conn, batch_id, [row for _n, row in clean])
    db.finish_batch(
        conn, batch_id, report.total_rows, report.valid_rows, report.rejected_rows
    )
    return batch_id


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry (S3 ObjectCreated -> SQS). Wired in serverless.yml later.

    boto3 is imported lazily so local runs never need the AWS SDK.
    """
    import io
    import json
    import urllib.parse

    import boto3

    s3 = boto3.client("s3")
    reports = []
    for record in event.get("Records", []):
        payload = json.loads(record["body"]) if "body" in record else record
        s3_record = payload.get("Records", [payload])[0].get("s3", {})
        bucket = s3_record["bucket"]["name"]
        key = urllib.parse.unquote_plus(s3_record["object"]["key"])
        obj = s3.get_object(Bucket=bucket, Key=key)
        text = io.TextIOWrapper(obj["Body"], encoding="utf-8-sig", newline="")
        reports.append(process_file(text, source_filename=key))
    return {
        "batches": [
            {"batch_id": str(r.batch_id), "valid": r.valid_rows, "rejected": r.rejected_rows}
            for r in reports
        ]
    }