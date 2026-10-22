# ADR-005: Match semantics — hard pass/fail, ranked, capped, measured

## Decision & Why
Eligibility is binary (SQL eligible_pairs): you meet the criteria or you don't — no
synthetic "95% match" scores (without underwriting actuarial data, scores mislead).
Ranking deterministic: interest_rate ASC (nulls last), product_id tie-break. Cap of
5 products per user (email readability). reason_codes + reason_text per match feed
the audit trail and the notification. LLM = 0 calls for eligibility; funnel stages
measured in match_runs (60,012 -> 36,822 SQL -> 34,718 rules on the 10k dataset).

## Where it fails
- NULL interest rate ranks last (missing data behind known deals) — documented.
- Cap truncates: user eligible for 6 sees 5; matches stores exactly what was sent.
- Two runs store two result sets (match_run_id key) — aggregates must be scoped
  by run; identical counts across runs confirm determinism.