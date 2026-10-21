from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from ingest.config import database_url

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parents[2]


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
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv_fallback()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def db_conn():
    """Connection for integration tests. Rolls back after each test (no data loss)."""
    try:
        conn = psycopg.connect(database_url())
    except Exception as exc:  
        pytest.skip(f"Postgres unavailable: {exc}")
    yield conn
    conn.rollback()
    conn.close()