# ADR-004: Crawl targets and extraction identity — chosen by evidence

## Context
Need 2-3 public personal-loan pages that are reachable, server-rendered, and
publish eligibility criteria; and a stable identity for extracted products.

## Options considered
1. Original plan: HDFC / ICICI / SBI
2. Reachable subset from a 10-target probe: Axis, Kotak, SBI (Bajaj attempted, failed extraction twice)
3. Aggregators (BankBazaar, Paisabazaar)

## Decision & Why
Option 2. Reconnaissance evidence: Axis/Kotak/SBI return 200 with real server-
rendered HTML and publish criteria; HDFC/ICICI/BoB tarpit or drop non-browser
clients (curl revealed HDFC/ICICI migrated to the .bank.in TLD); PNB and both
aggregators fail DNS from the deployment network. Two extraction bugs shaped the
design: (a) LLM name variance created duplicate rows -> product identity is now
OUR configured source_name, never the LLM's label; (b) a run that failed to
re-extract a field wiped it with NULL -> upsert now uses COALESCE last-known-good
merge. A page that fails extraction is isolated (crawl_runs 'failed') and
time-boxed; Bajaj was swapped for SBI after two failures.

## Where it fails
- Reachability is network-dependent (AWS may resolve differently): the source
  list is data in one node, not code - swapping is one edit.
- COALESCE merge keeps stale values if a criterion is removed from the page:
  accepted trade-off for lossy extraction; criteria_raw always shows latest evidence.
- SBI publishes no credit score -> NULL = unconstrained (ADR-002); missing_fields
  recorded in criteria_raw.
- LLM extraction is untrusted: prompt-injection defense is layered (text framed as
  data, ignore-instructions system prompt, temp 0, JSON validation, enum clamping,
  parameterized/escaped SQL, DB CHECKs as final gate).