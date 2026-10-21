from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ[key.strip()] = val.strip().strip("'\"")


def database_url() -> str:
    _load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please define it in your .env or export it in your shell."
        )
    return url


def upload_dir() -> Path:
    _load_dotenv()
    return Path(os.environ.get("UPLOAD_DIR", "data/uploads"))