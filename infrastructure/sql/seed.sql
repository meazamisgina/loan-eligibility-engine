BEGIN;

INSERT INTO loan_products
    (product_name, source_url, interest_rate, min_monthly_income, min_credit_score,
     max_credit_score, min_age, max_age, allowed_employment)
VALUES
    ('SBI Personal Loan (seed)',   'https://example.com/sbi',   10.50, 25000, 650, 850, 21, 60, ARRAY['Salaried','Self-Employed']),
    ('HDFC Personal Loan (seed)',  'https://example.com/hdfc',  11.20, 30000, 700, 850, 21, 58, ARRAY['Salaried','Business']),
    ('ICICI Personal Loan (seed)', 'https://example.com/icici', 10.99, 20000, 660, 850, 23, 65, ARRAY['Salaried','Self-Employed','Business']);

INSERT INTO users
    (user_id, name, email, monthly_income, credit_score, employment_status, age)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'Test User One', 'test.one@example.com', 50000, 720, 'Salaried', 30),
    ('00000000-0000-0000-0000-000000000002', 'Test User Two', 'test.two@example.com', 15000, 600, 'Business', 45);

COMMIT;