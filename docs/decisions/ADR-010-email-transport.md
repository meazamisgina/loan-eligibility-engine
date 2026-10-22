# ADR-010: Email transport — SES production, SMTP->Mailpit local

## Decision & Why
Workflow C ships the AWS SES node (the assignment's required production transport)
behind an IF: transport=ses -> SES node; transport=smtp -> SMTP node -> Mailpit
(local Docker catcher). SES requires an AWS account + sandbox verification of
recipients; the local demo therefore runs SMTP, and the demo sends ONLY to
configured Gmail +aliases (assignment rule: never email the CSV addresses).

## Where it fails
- SES sandbox limits recipients to verified identities (documented; the +alias
  pattern exists precisely for this).
- Mailpit is a test harness: nothing it sends is real mail. Documented in README.