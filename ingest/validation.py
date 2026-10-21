from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

REQUIRED_COLUMNS = (
    "user_id",
    "name",
    "email",
    "monthly_income",
    "credit_score",
    "employment_status",
    "age",
)

EMPLOYMENT_STATUSES = {
    "salaried": "Salaried",
    "self-employed": "Self-Employed",
    "business": "Business",
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_CREDIT_SCORE, MAX_CREDIT_SCORE = 300, 900
MIN_AGE, MAX_AGE = 18, 120


@dataclass(frozen=True)
class CleanRow:
    user_id: str
    name: str
    email: str
    monthly_income: Decimal
    credit_score: int
    employment_status: str
    age: int


def check_columns(fieldnames: list[str] | None) -> str | None:
    if not fieldnames:
        return "empty or unreadable CSV header"
    normalized = [(name or "").strip().lower() for name in fieldnames]
    missing = [column for column in REQUIRED_COLUMNS if column not in normalized]
    if missing:
        return f"missing required columns: {', '.join(missing)}"
    return None


def validate_row(raw: dict[str, Any]) -> tuple[CleanRow | None, str | None]:
    try:
        user_id = str(UUID(str(raw.get("user_id")).strip()))
    except (ValueError, AttributeError, TypeError):
        return None, f"invalid user_id: {raw.get('user_id')!r}"

    name = (raw.get("name") or "").strip()
    if not name:
        return None, "empty name"

    email = (raw.get("email") or "").strip()
    if not EMAIL_RE.match(email):
        return None, f"invalid email: {email!r}"

    income_value = (raw.get("monthly_income") or "").replace(",", "").strip()
    try:
        monthly_income = Decimal(income_value)
    except InvalidOperation:
        return None, f"invalid monthly_income: {raw.get('monthly_income')!r}"
    if monthly_income <= 0:
        return None, f"monthly_income must be > 0, got {monthly_income}"

    try:
        credit_score = int(str(raw.get("credit_score")).strip())
    except (ValueError, TypeError):
        return None, f"invalid credit_score: {raw.get('credit_score')!r}"
    if not MIN_CREDIT_SCORE <= credit_score <= MAX_CREDIT_SCORE:
        return None, (
            f"credit_score out of range {MIN_CREDIT_SCORE}-{MAX_CREDIT_SCORE}: {credit_score}"
        )

    employment_key = (raw.get("employment_status") or "").strip().lower()
    employment_status = EMPLOYMENT_STATUSES.get(employment_key)
    if employment_status is None:
        return None, f"invalid employment_status: {raw.get('employment_status')!r}"

    try:
        age = int(str(raw.get("age")).strip())
    except (ValueError, TypeError):
        return None, f"invalid age: {raw.get('age')!r}"
    if not MIN_AGE <= age <= MAX_AGE:
        return None, f"age out of range {MIN_AGE}-{MAX_AGE}: {age}"

    clean = CleanRow(
        user_id=user_id,
        name=name,
        email=email,
        monthly_income=monthly_income,
        credit_score=credit_score,
        employment_status=employment_status,
        age=age,
    )
    return clean, None