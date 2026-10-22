from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from ingest.config import upload_dir
from ingest.handler import process_file

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  
ALLOWED_EXTENSIONS = {".csv"}
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="Loan Eligibility Engine - Upload API")


def _match_webhook_url() -> str:
    return os.environ.get(
        "MATCH_WEBHOOK_URL", "http://localhost:5678/webhook/match-run"
    )


def _trigger_matching(batch_id: str) -> bool:
    """Best-effort trigger of Workflow B. Never fails the upload itself."""
    body = ('{"batch_id": "' + batch_id + '"}').encode("utf-8")
    request = urllib.request.Request(
        _match_webhook_url(),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("match webhook trigger failed: %s", exc)
        return False


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="only .csv files are accepted")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 20MB limit")

    target = upload_dir() / f"{uuid.uuid4().hex}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    report = process_file(target, source_filename=file.filename or target.name)

    triggered = False
    if report.error is None:
        triggered = _trigger_matching(str(report.batch_id))

    return {
        "batch_id": str(report.batch_id),
        "source_filename": report.source_filename,
        "total_rows": report.total_rows,
        "valid_rows": report.valid_rows,
        "rejected_rows": report.rejected_rows,
        "rejections": [
            {"row": row_number, "reason": reason}
            for row_number, reason in report.rejections[:10]
        ],
        "pipeline_triggered": triggered,
        "error": report.error,
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")