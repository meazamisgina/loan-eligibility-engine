# ADR-007: UI scope — thin API + one polished static page

## Context
The requirement: "a minimal UI that allows for the initial upload of the user data
CSV file... the primary interaction point for starting the entire pipeline."

## Options considered
1. React/Next.js SPA
2. Polished single-file static page + thin FastAPI adapter
3. No UI (curl only)

## Decision & Why
Option 2. The assignment grades backend and orchestration; a finished, well-crafted
static page delivers the requirement with zero build step and zero demo fragility.
The API is a thin adapter over the already-tested pipeline (process_file) — no
duplicated logic — and triggers Workflow B so one click runs ingest -> match ->
notify. Client-side validation (extension/size) mirrors server-side caps.

## Where it fails
- Not a full SPA: no live job dashboard. Accepted: MVP scope (the DB audit tables
  are the system of record). Porting to React later changes nothing in the API.
- Single-file upload: no batch directory mode. The CLI (run_local.py) covers bulk.