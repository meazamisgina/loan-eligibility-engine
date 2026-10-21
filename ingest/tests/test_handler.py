from __future__ import annotations

import pytest

from ingest.handler import parse_and_validate


def _read(fixtures_dir, name):
    return (fixtures_dir / name).open("r", encoding="utf-8", newline="")


def test_valid_file_all_clean(fixtures_dir):
    with _read(fixtures_dir, "users_valid_small.csv") as handle:
        staging, clean, rejected = parse_and_validate(handle)
    assert (len(staging), len(clean), len(rejected)) == (3, 3, 0)


def test_mixed_file_quarantines_bad_rows(fixtures_dir):
    with _read(fixtures_dir, "users_bad_types.csv") as handle:
        staging, clean, rejected = parse_and_validate(handle)
    assert (len(staging), len(clean), len(rejected)) == (2, 1, 1)
    assert "monthly_income must be > 0" in rejected[0][2]


def test_duplicate_ids_first_wins(fixtures_dir):
    with _read(fixtures_dir, "users_duplicate_ids.csv") as handle:
        _staging, clean, rejected = parse_and_validate(handle)
    assert len(clean) == 1
    assert clean[0][1].name == "First Wins"
    assert "duplicate user_id in file" in rejected[0][2]


def test_missing_columns_raises_for_file_level_error(fixtures_dir):
    with _read(fixtures_dir, "users_missing_columns.csv") as handle:
        with pytest.raises(ValueError, match="missing required columns"):
            parse_and_validate(handle)


def test_malicious_rows_are_inert(fixtures_dir):
    with _read(fixtures_dir, "users_malicious.csv") as handle:
        _staging, clean, rejected = parse_and_validate(handle)
    assert (len(clean), len(rejected)) == (2, 0)
    assert clean[0][1].name == "'); DROP TABLE users; --"