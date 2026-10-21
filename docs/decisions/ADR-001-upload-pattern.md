# ADR-001: Event-driven CSV upload instead of direct API upload

## Context
Bulk CSV upload is the entry point of the whole pipeline. The assignment notes that
"direct upload through a standard Lambda-backed API Gateway endpoint can hit request
size and timeout limits" and asks for "a more professional, event-driven pattern."
Scale: ~10,000-row files today, but the design must not break at 10×.

## Options considered
1. POST file through API Gateway → Lambda parses in-request
2. Presigned URL → object storage (S3/MinIO) → storage event → queue → ingest Lambda
3. Browser → directly into the database via a long-lived connection

## Decision & Why
Option 2. The file never passes through compute: the browser uploads straight to
object storage via a presigned URL (upload scales with the client, no request-size
or timeout ceiling). A storage event pushes to a queue, which decouples upload from
processing: retries, backpressure, and no lost files if the ingest worker is down.
Option 3 skips validation and audit entirely and exposes the database — rejected.

## Where it fails
- Event delivery is at-least-once → duplicates possible; mitigated by idempotent
  upsert on user_id (see ADR-008).
- Presigned URLs can be shared before expiry → short TTL (e.g. 10 min) + one URL per
  file, bucket is private.
- Queue consumer scaling is limited by DB connection count → batch inserts + capped
  concurrency.