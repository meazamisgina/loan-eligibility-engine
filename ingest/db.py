from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ingest.config import database_url
from ingest.validation import CleanRow

UPSERT_USERS_SQL = """
    INSERT INTO users
        (user_id, name, email, monthly_income, credit_score, employment_status, age, batch_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE SET
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        monthly_income = EXCLUDED.monthly_income,
        credit_score = EXCLUDED.credit_score,
        employment_status = EXCLUDED.employment_status,
        age = EXCLUDED.age,
        batch_id = EXCLUDED.batch_id,
        updated_at = now()
    -- ingested_at is intentionally preserved: it records the first-ever ingestion.
"""


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url())


def create_batch(conn: psycopg.Connection, source_filename: str) -> UUID:
    row = conn.execute(
        "INSERT INTO ingestion_batches (source_filename, status) "
        "VALUES (%s, 'processing') RETURNING batch_id",
        (source_filename,),
    ).fetchone()
    return row[0]


def record_staging(
    conn: psycopg.Connection, batch_id: UUID, rows: Iterable[tuple[int, dict[str, Any]]]
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO users_staging (batch_id, row_number, raw) VALUES (%s, %s, %s)",
            [(batch_id, number, Jsonb(raw)) for number, raw in rows],
        )


def record_rejected(
    conn: psycopg.Connection,
    batch_id: UUID,
    rows: Iterable[tuple[int, dict[str, Any], str]],
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO users_rejected (batch_id, row_number, raw, error_reason) "
            "VALUES (%s, %s, %s, %s)",
            [(batch_id, number, Jsonb(raw), reason) for number, raw, reason in rows],
        )


def upsert_users(
    conn: psycopg.Connection, batch_id: UUID, rows: Iterable[CleanRow]
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            UPSERT_USERS_SQL,
            [
                (
                    row.user_id,
                    row.name,
                    row.email,
                    row.monthly_income,
                    row.credit_score,
                    row.employment_status,
                    row.age,
                    batch_id,
                )
                for row in rows
            ],
        )


def finish_batch(
    conn: psycopg.Connection,
    batch_id: UUID,
    total: int,
    valid: int,
    rejected: int,
    status: str = "completed",
    error: str | None = None,
) -> None:
    conn.execute(
        "UPDATE ingestion_batches SET status = %s, total_rows = %s, valid_rows = %s, "
        "rejected_rows = %s, error = %s, finished_at = now() WHERE batch_id = %s",
        (status, total, valid, rejected, error, batch_id),
    )