from __future__ import annotations

from decimal import Decimal

from ingest.validation import validate_row

VALID = {
    "user_id": "11111111-1111-1111-1111-111111111111",
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "monthly_income": "50000",
    "credit_score": "720",
    "employment_status": "Salaried",
    "age": "30",
}


def _row(**overrides):
    return {**VALID, **overrides}


def test_valid_row_passes():
    row, reason = validate_row(_row())
    assert reason is None
    assert row is not None
    assert row.credit_score == 720


def test_income_with_comma_is_normalized():
    row, reason = validate_row(_row(monthly_income="73,000"))
    assert reason is None
    assert row.monthly_income == Decimal("73000")


def test_employment_case_is_normalized():
    row, reason = validate_row(_row(employment_status="self-employed"))
    assert reason is None
    assert row.employment_status == "Self-Employed"


def test_bad_user_id_rejected():
    row, reason = validate_row(_row(user_id="not-a-uuid"))
    assert row is None
    assert "invalid user_id" in reason


def test_empty_name_rejected():
    row, reason = validate_row(_row(name="   "))
    assert row is None
    assert "empty name" in reason


def test_bad_email_rejected():
    row, reason = validate_row(_row(email="pooja.chopra@exa"))
    assert row is None
    assert "invalid email" in reason


def test_zero_income_rejected():
    row, reason = validate_row(_row(monthly_income="0"))
    assert row is None
    assert "monthly_income must be > 0" in reason


def test_credit_score_out_of_range_rejected():
    row, reason = validate_row(_row(credit_score="200"))
    assert row is None
    assert "credit_score out of range" in reason


def test_unknown_employment_rejected():
    row, reason = validate_row(_row(employment_status="Unemployed"))
    assert row is None
    assert "invalid employment_status" in reason


def test_age_out_of_range_rejected():
    row, reason = validate_row(_row(age="12"))
    assert row is None
    assert "age out of range" in reason


def test_injection_strings_survive_as_literal_text():
    row, reason = validate_row(_row(name="'); DROP TABLE users; --"))
    assert reason is None
    assert row.name == "'); DROP TABLE users; --"