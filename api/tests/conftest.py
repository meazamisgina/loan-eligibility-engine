from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from ingest.config import database_url

FIXTURES = Path(__file__).resolve().parents[2] / "ingest" / "tests" / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_IDS = [
    "11111111-1111-1111-1111-111111111111",
    "22222222-2222-2222-2222-222222222222",
    "33333333-3333-3333-3333-333333333333",
]


def _load_dotenv_fallback() -> None:
    if "DATABASE_URL" in os.environ:
        return
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv_fallback()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def db_conn():
    try:
        conn = psycopg.connect(database_url())
    except Exception as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    pre_existing = {
        row[0]
        for row in conn.execute("SELECT batch_id FROM ingestion_batches").fetchall()
    }
    yield conn

    created = [
        row[0]
        for row in conn.execute("SELECT batch_id FROM ingestion_batches").fetchall()
        if row[0] not in pre_existing
    ]
    if created:
        conn.execute("DELETE FROM users WHERE batch_id = ANY(%s)", (created,))
        conn.execute(
            "DELETE FROM ingestion_batches WHERE batch_id = ANY(%s)", (created,)
        )
    conn.execute("DELETE FROM users WHERE user_id = ANY(%s)", (FIXTURE_IDS,))
    conn.commit()
    conn.close()