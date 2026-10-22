# ADR-003: SQL-first matching funnel — the LLM never judges eligibility

## Context
~10,000 users x ~6 products = ~60k candidate pairs. Evaluating each with an LLM
would be "extremely slow and expensive" (assignment). Eligibility must be explainable.

## Options considered
1. LLM evaluates every user-product pair
2. SQL pre-filter -> deterministic n8n rules -> LLM for language only

## Decision & Why
Option 2. Eligibility is a pure function of published criteria: SQL eliminates
impossible pairs exactly (eligible_pairs view), n8n applies business rules
(rank, cap), and the LLM is used only for extracting criteria from messy pages
(Workflow A). Result on the 10k dataset: 60,012 pairs -> 36,822 (SQL) -> 34,718
(rules) with 0 LLM calls. A lender must explain a rejection; a model cannot.

## Where it fails
- Criteria that cannot be expressed numerically (e.g. "stable employment") would
  need the LLM stage; mitigated by keeping criteria_raw for future rule work.
- NULL criteria = unconstrained (ADR-002) can over-match; missing_fields recorded
  in criteria_raw makes this visible.