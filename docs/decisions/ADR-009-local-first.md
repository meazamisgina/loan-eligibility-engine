# ADR-009: Local-first development and demo, with AWS as a documented deployment target

## Context
The assignment requires AWS services (Lambda, RDS, SES) and notes "Local deployment
is acceptable; public deployment on AWS is a plus, not a requirement. You are not
expected to incur cloud costs." The reviewer must be able to run the entire system
with one command. The builder (this project) has no AWS account during development.

## Options considered
1. Build against live AWS only (requires account + card + billing risk)
2. Local-first via Docker Compose (Postgres, n8n, Mailpit), with serverless.yml as
   validated Infrastructure-as-Code for AWS
3. Mock everything with in-memory fakes (no real Postgres, no real SMTP)

## Decision & Why
Option 2. Local-first guarantees a reproducible one-command demo
(`docker compose up -d`) with zero cost and zero network dependency — live cloud
demos fail for reasons outside the presenter's control. Real infrastructure
underneath (real Postgres 16, real self-hosted n8n, real SMTP delivery to Mailpit)
means the local run exercises the same SQL, the same workflows, and the same email
path as production. serverless.yml documents the AWS deployment precisely and is
validated offline via `serverless print` — proving the cloud architecture without
requiring an account. Option 3 was rejected: mocks don't prove the schema, the
queries, or the delivery path.

## Where it fails
- Local networking differs from AWS (no SQS event source locally; the local
  drop-folder/API upload drives ingestion directly). Mitigation: the ingest layer
  is transport-agnostic (ADR-001) — the same handler runs from a file path locally
  and from an S3 event on AWS.
- n8n credentials differ per environment (Postgres host `postgres` in Docker vs an
  RDS endpoint on AWS). Documented in the README setup section.

## AWS mapping (serverless.yml)
MinIO/drop-folder -> S3 uploads bucket (ObjectCreated -> SQS -> Lambda); Postgres
container -> RDS (Lambda in private subnets); Mailpit -> SES. The Lambda handler is
the same ingest/handler.py used locally — the transport changed, the logic did not.
Deploy is env-driven and validates offline via `serverless print`; live deployment
is optional per the assignment ("local deployment is acceptable"). S3 -> SQS queue
policy is wired explicitly (S3 enqueue fails silently without it).

serverless.yml lives at the repo root, not in infrastructure/: the framework
resolves handler paths against the service directory, so a config inside
infrastructure/ would package the wrong paths. The assignment does not mandate
a path; root placement matches framework convention.
