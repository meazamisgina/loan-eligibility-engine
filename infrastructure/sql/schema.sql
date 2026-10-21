CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'processing', 'completed', 'failed')),
    total_rows      INTEGER NOT NULL DEFAULT 0,
    valid_rows      INTEGER NOT NULL DEFAULT 0,
    rejected_rows   INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS users_staging (
    batch_id   UUID NOT NULL REFERENCES ingestion_batches (batch_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    raw        JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS users_rejected (
    batch_id     UUID NOT NULL REFERENCES ingestion_batches (batch_id) ON DELETE CASCADE,
    row_number   INTEGER NOT NULL,
    raw          JSONB NOT NULL,
    error_reason TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (batch_id, row_number)
);

CREATE TABLE IF NOT EXISTS users (
    user_id           UUID PRIMARY KEY,
    name              TEXT NOT NULL,
    email             TEXT NOT NULL,
    monthly_income    NUMERIC(12,2) NOT NULL CHECK (monthly_income > 0),
    credit_score      INTEGER NOT NULL CHECK (credit_score BETWEEN 300 AND 900),
    employment_status TEXT NOT NULL
        CHECK (employment_status IN ('Salaried', 'Self-Employed', 'Business')),
    age               INTEGER NOT NULL CHECK (age BETWEEN 18 AND 120),
    batch_id          UUID REFERENCES ingestion_batches (batch_id),
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_credit_score ON users (credit_score);
CREATE INDEX IF NOT EXISTS idx_users_income       ON users (monthly_income);
CREATE INDEX IF NOT EXISTS idx_users_employment   ON users (employment_status);

CREATE TABLE IF NOT EXISTS crawl_runs (
    crawl_run_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url     TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    http_status    INTEGER,
    products_found INTEGER NOT NULL DEFAULT 0,
    error          TEXT,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_source ON crawl_runs (source_url, started_at DESC);

CREATE TABLE IF NOT EXISTS loan_products (
    product_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name       TEXT NOT NULL,
    source_url         TEXT NOT NULL,
    interest_rate      NUMERIC(5,2) CHECK (interest_rate >= 0),
    min_monthly_income NUMERIC(12,2) CHECK (min_monthly_income >= 0),
    min_credit_score   INTEGER CHECK (min_credit_score BETWEEN 300 AND 900),
    max_credit_score   INTEGER CHECK (max_credit_score BETWEEN 300 AND 900),
    min_age            INTEGER CHECK (min_age BETWEEN 18 AND 120),
    max_age            INTEGER CHECK (max_age BETWEEN 18 AND 120),
    allowed_employment TEXT[] CHECK (allowed_employment <@ ARRAY['Salaried','Self-Employed','Business']),
    criteria_raw       JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_hash       TEXT,
    crawl_run_id       UUID REFERENCES crawl_runs (crawl_run_id),
    first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_url, product_name)
);

CREATE INDEX IF NOT EXISTS idx_products_credit_range ON loan_products (min_credit_score, max_credit_score);

CREATE TABLE IF NOT EXISTS match_runs (
    match_run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status              TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    users_processed     INTEGER NOT NULL DEFAULT 0,
    pairs_before_filter INTEGER NOT NULL DEFAULT 0,
    pairs_after_sql     INTEGER NOT NULL DEFAULT 0,
    pairs_after_rules   INTEGER NOT NULL DEFAULT 0,
    llm_calls_made      INTEGER NOT NULL DEFAULT 0,
    note                TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS matches (
    user_id      UUID NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    product_id   UUID NOT NULL REFERENCES loan_products (product_id) ON DELETE CASCADE,
    match_run_id UUID NOT NULL REFERENCES match_runs (match_run_id) ON DELETE CASCADE,
    reason_codes TEXT[] NOT NULL DEFAULT '{}',
    reason_text  TEXT,
    matched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, product_id, match_run_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_user ON matches (user_id);
CREATE INDEX IF NOT EXISTS idx_matches_run  ON matches (match_run_id);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    match_run_id    UUID NOT NULL REFERENCES match_runs (match_run_id) ON DELETE CASCADE,
    recipient_alias TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'smtp' CHECK (channel IN ('smtp', 'ses')),
    message_id      TEXT,
    status          TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'failed')),
    error           TEXT,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_run ON notifications (match_run_id);

-- Stage 1 Funnel: SQL set-based pre-filter view consumed by Workflow B
CREATE OR REPLACE VIEW eligible_pairs AS
SELECT
    u.user_id,
    p.product_id,
    p.interest_rate,
    ARRAY_REMOVE(ARRAY[
        CASE WHEN p.min_monthly_income IS NULL
              OR u.monthly_income >= p.min_monthly_income
             THEN 'income_ok' END,
        CASE WHEN (p.min_credit_score IS NULL OR u.credit_score >= p.min_credit_score)
          AND (p.max_credit_score IS NULL OR u.credit_score <= p.max_credit_score)
             THEN 'credit_ok' END,
        CASE WHEN p.allowed_employment IS NULL
              OR u.employment_status = ANY (p.allowed_employment)
             THEN 'employment_ok' END,
        CASE WHEN (p.min_age IS NULL OR u.age >= p.min_age)
          AND (p.max_age IS NULL OR u.age <= p.max_age)
             THEN 'age_ok' END
    ], NULL) AS reason_codes
FROM users u
JOIN loan_products p
  ON (p.min_monthly_income IS NULL OR u.monthly_income >= p.min_monthly_income)
 AND (p.min_credit_score  IS NULL OR u.credit_score >= p.min_credit_score)
 AND (p.max_credit_score  IS NULL OR u.credit_score <= p.max_credit_score)
 AND (p.allowed_employment IS NULL OR u.employment_status = ANY (p.allowed_employment))
 AND (p.min_age IS NULL OR u.age >= p.min_age)
 AND (p.max_age IS NULL OR u.age <= p.max_age);