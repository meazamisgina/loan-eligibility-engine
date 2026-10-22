from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client(db_conn):
    return TestClient(app)


def _upload(fixtures_dir, name, content=None, filename=None):
    path = fixtures_dir / name
    data = content if content is not None else path.read_bytes()
    return TestClient(app).post(
        "/api/upload",
        files={"file": (filename or name, data, "text/csv")},
    )


def test_valid_file_reports_clean(db_conn, fixtures_dir):
    response = _upload(fixtures_dir, "users_valid_small.csv")
    assert response.status_code == 200
    body = response.json()
    assert (body["total_rows"], body["valid_rows"], body["rejected_rows"]) == (3, 3, 0)
    assert body["error"] is None
    assert isinstance(body["pipeline_triggered"], bool)


def test_mixed_file_quarantines_bad_rows(db_conn, fixtures_dir):
    response = _upload(fixtures_dir, "users_bad_types.csv")
    body = response.json()
    assert (body["valid_rows"], body["rejected_rows"]) == (1, 1)
    assert "monthly_income must be > 0" in body["rejections"][0]["reason"]


def test_missing_columns_reported_as_file_error(db_conn, fixtures_dir):
    response = _upload(fixtures_dir, "users_missing_columns.csv")
    body = response.json()
    assert body["error"] is not None
    assert "missing required columns" in body["error"]


def test_malicious_rows_stored_inert(db_conn, fixtures_dir):
    response = _upload(fixtures_dir, "users_malicious.csv")
    body = response.json()
    assert (body["valid_rows"], body["rejected_rows"]) == (2, 0)


def test_wrong_extension_rejected(db_conn):
    response = TestClient(app).post(
        "/api/upload", files={"file": ("evil.txt", b"not a csv", "text/plain")}
    )
    assert response.status_code == 400


def test_empty_file_rejected(db_conn):
    response = TestClient(app).post(
        "/api/upload", files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert response.status_code == 400


def test_oversized_file_rejected(db_conn, monkeypatch):
    monkeypatch.setattr("api.main.MAX_UPLOAD_BYTES", 10)
    response = TestClient(app).post(
        "/api/upload", files={"file": ("big.csv", b"x" * 100, "text/csv")}
    )
    assert response.status_code == 413