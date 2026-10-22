# ADR-006: Notification email — deterministic template, no LLM

## Decision & Why
Customer emails are built 100% from the matches table via a template. In fintech,
customer communications carry compliance risk: an LLM hallucinating a promised
interest rate makes the company liable. A template guarantees the email contains
exactly what the database says. Same input -> same email (demo reproducibility).

## Where it fails
- Rigid wording; polish is manual. Accepted: correctness beats cleverness in
  customer comms.