# ADR-011: Secret handling — two places only, ever

## Decision & Why
Credentials live only in `.env` (gitignored) and n8n's encrypted credential store.
The repo carries `.env.example` placeholders only. `git status` is checked before
every commit; exported workflow JSONs are scanned for `sk-` before committing.
A leaked key is treated as compromised: revoke first, replace second — during
development a shared test key appeared in a debugging transcript and was flagged
immediately (rotation belonged to the key's owner).

## Where it fails
- Screenshots and screen recordings are leak vectors: the demo video avoids the
  n8n credentials panel by design.
- `git history is forever`: cleanup is not a substitute for revocation.