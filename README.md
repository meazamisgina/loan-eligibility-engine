# Loan Eligibility Engine

Automated pipeline that ingests user CSV data, discovers personal loan products
from public websites, matches users to eligible products, and notifies them.

## Status
- In progress - see the task board in Pull Requests.

## Architecture
(coming: docs/architecture.md)

## Quick Start
(coming: `docker compose up` → open UI at http://localhost:5173, n8n at http://localhost:5678)

## Design Decisions
Every non-trivial choice is documented in `docs/decisions/` as an ADR
(Context → Options → Decision & Why → Where it fails).

## Deliverables Checklist
- [ ] Infrastructure: serverless.yml, docker-compose.yml, n8n workflow JSONs
- [ ] Data ingestion pipeline (CSV → validation → PostgreSQL)
- [ ] Workflow A: Loan Product Discovery (crawler)
- [ ] Workflow B: User–Loan Matching (optimization funnel)
- [ ] Workflow C: User Notification (SES)
- [ ] Frontend: CSV upload UI
- [ ] Documentation: architecture diagram, setup guide, design decisions
- [ ] Demo video (5–10 min)