"""Integration tests against the local Postgres (docker compose up).

Each test runs in a transaction that is rolled back afterwards. Every assertion
is scoped (by batch_id, fixture user_ids, or test-owned product_id) on BOTH sides
of each join so tests pass regardless of what else is committed in the database
(seed rows, real datasets). Tests must be independent of committed state.
"""
from __future__ import annotations

from ingest.handler import process_file

FIXTURE_IDS = [
    "11111111-1111-1111-1111-111111111111",
    "22222222-2222-2222-2222-222222222222",
    "33333333-3333-3333-3333-333333333333",
]

FUNNEL_TEST_USER_IDS = [
    "aaaaaaaa-0000-0000-0000-000000000001",
    "aaaaaaaa-0000-0000-0000-000000000002",
    "aaaaaaaa-0000-0000-0000-000000000003",
]


def test_valid_file_lands_in_all_tables(db_conn, fixtures_dir):
    report = process_file(fixtures_dir / "users_valid_small.csv", conn=db_conn)
    assert (report.total_rows, report.valid_rows, report.rejected_rows) == (3, 3, 0)
    users = db_conn.execute(
        "SELECT count(*) FROM users WHERE user_id = ANY(%s)", (FIXTURE_IDS,)
    ).fetchone()[0]
    assert users == 3
    staging = db_conn.execute(
        "SELECT count(*) FROM users_staging WHERE batch_id = %s", (report.batch_id,)
    ).fetchone()[0]
    assert staging == 3
    batch = db_conn.execute(
        "SELECT total_rows, valid_rows, status FROM ingestion_batches WHERE batch_id = %s",
        (report.batch_id,),
    ).fetchone()
    assert batch == (3, 3, "completed")


def test_reupload_is_idempotent(db_conn, fixtures_dir):
    path = fixtures_dir / "users_valid_small.csv"
    first = process_file(path, conn=db_conn)
    second = process_file(path, conn=db_conn)  # same file again
    assert db_conn.execute(
        "SELECT count(*) FROM users WHERE user_id = ANY(%s)", (FIXTURE_IDS,)
    ).fetchone()[0] == 3
    # Audit trail keeps every upload: 3 staging rows per batch, 2 batches.
    for batch_id in (first.batch_id, second.batch_id):
        staging = db_conn.execute(
            "SELECT count(*) FROM users_staging WHERE batch_id = %s", (batch_id,)
        ).fetchone()[0]
        assert staging == 3


def test_rejected_rows_carry_reasons(db_conn, fixtures_dir):
    report = process_file(fixtures_dir / "users_bad_types.csv", conn=db_conn)
    reason = db_conn.execute(
        "SELECT error_reason FROM users_rejected WHERE batch_id = %s",
        (report.batch_id,),
    ).fetchone()[0]
    assert "monthly_income must be > 0" in reason


def test_bad_header_marks_batch_failed(db_conn, fixtures_dir):
    report = process_file(fixtures_dir / "users_missing_columns.csv", conn=db_conn)
    assert report.error is not None
    status = db_conn.execute(
        "SELECT status FROM ingestion_batches WHERE batch_id = %s", (report.batch_id,)
    ).fetchone()[0]
    assert status == "failed"


def test_malicious_names_stored_as_inert_text(db_conn, fixtures_dir):
    process_file(fixtures_dir / "users_malicious.csv", conn=db_conn)
    names = db_conn.execute(
        "SELECT name FROM users WHERE user_id::text LIKE '66666666-%' "
        "OR user_id::text LIKE '77777777-%' ORDER BY name"
    ).fetchall()
    assert ("'); DROP TABLE users; --",) in names  # stored literally, no injection
    assert ("=cmd|'/C calc'!A0",) in names


def test_bom_and_crlf_file_loads(db_conn, tmp_path):
    content = (
        b"\xef\xbb\xbf"  # UTF-8 BOM
        b"user_id,name,email,monthly_income,credit_score,employment_status,age\r\n"
        b"88888888-8888-8888-8888-888888888888,Bom User,bom.user@example.com,50000,"
        b"700,Salaried,30\r\n"
    )
    path = tmp_path / "bom.csv"
    path.write_bytes(content)
    report = process_file(path, conn=db_conn)
    assert (report.total_rows, report.valid_rows) == (1, 1)


def test_funnel_discriminates_matching(db_conn):
    """Stage-1 pre-filter: the matching user passes, the others don't.

    Scoped on BOTH sides: WHERE product_id = test product AND user_id IN (test
    users). Scoping one side alone leaked committed data (seed products added 5
    pairs -> 6 == 1; seed user one matched the test product -> 2 == 1).
    """
    product_id = db_conn.execute(
        """
        INSERT INTO loan_products (product_name, source_url, min_monthly_income,
                                   min_credit_score, max_credit_score, allowed_employment)
        VALUES ('Funnel Test Loan', 'https://example.com/funnel-test',
                40000, 650, 850, ARRAY['Salaried'])
        RETURNING product_id
        """
    ).fetchone()[0]
    db_conn.execute(
        """
        INSERT INTO users (user_id, name, email, monthly_income, credit_score,
                           employment_status, age)
        VALUES ('aaaaaaaa-0000-0000-0000-000000000001', 'Matches',  'matches@example.com',
                50000, 700, 'Salaried', 30),
               ('aaaaaaaa-0000-0000-0000-000000000002', 'Too Poor', 'poor@example.com',
                10000, 700, 'Salaried', 30),
               ('aaaaaaaa-0000-0000-0000-000000000003', 'Wrong Job','wrong@example.com',
                50000, 700, 'Business', 30)
        """
    )
    pairs = db_conn.execute(
        "SELECT user_id, reason_codes FROM eligible_pairs "
        "WHERE product_id = %s AND user_id = ANY(%s)",
        (product_id, FUNNEL_TEST_USER_IDS),
    ).fetchall()
    assert len(pairs) == 1
    assert str(pairs[0][0]) == "aaaaaaaa-0000-0000-0000-000000000001"
    assert set(pairs[0][1]) == {"income_ok", "credit_ok", "employment_ok", "age_ok"}