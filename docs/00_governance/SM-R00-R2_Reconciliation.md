# SM-R00-R2 Requirements Reconciliation and Contract Validation

## Baseline comparison
The R1 catalog contained 35 requirement IDs. The Owner supplied a 41-capability baseline; the six individually verifiable baseline capabilities below were not represented by standalone IDs. They are restored without deleting or shrinking existing requirements.

| Baseline capability | R1 disposition | R2 ID / classification | Acceptance reference |
|---|---|---|---|
| Installable Windows 10/11 client | Missing standalone requirement | WIN-001 / RENAMED (platform capability made explicit) | AT-WIN-01 |
| System tray and automatic start | Combined within MSG-008 | WIN-002 / MERGED resolution (separate testable contract) | AT-WIN-02 |
| Signed automatic updates | Combined within MSG-008 | WIN-003 / MERGED resolution (separate security contract) | AT-WIN-03 |
| Private object storage plus malware gate | Combined within MSG-007 | ATT-001 / MERGED resolution (separate security contract) | AT-ATT-01 |
| Task calendar presentation shared with scheduling | Implied in TASK-005/UI | TASK-009 / RENAMED (explicit functional contract) | AT-TASK-09 |
| Initial concurrency/delivery target | NFR-004 had no target | OPS-001 / RENAMED (explicit measurable contract) | AT-OPS-01 |

The other 35 requirements are **PRESERVED**. After R2: 41 requirements exist; no baseline capability is missing or conflicted. R2 adds no product feature outside the Owner's explicit decisions; it decomposes previously bundled/implicit capability into verifiable contracts.

## Decision impact and implementation gates
ADR-004 through ADR-010 are applied in Decision Log. OD-001 retention/scanner product blocks attachment release; OD-002 session expiration blocks final production authentication configuration; OD-003 AI retention/notice blocks external AI activation; OD-004 update distribution/signing operations block automatic-update release. These are not blockers to documentation or non-policy-dependent R01 preparation.

## Contract cross-validation
| Contract | Requirements | Design locations | Tests | Result |
|---|---|---|---|---|
| Authentication / API / DB | AUTH-001..004 | DOC-06 accounts/sessions/audit; DOC-07 auth; DOC-09 session | AT-AUTH-01..04 | No inconsistency found |
| WebSocket / persistence / reconnect | MSG-001..004 | DOC-05 flow; DOC-06 messages/delivery; DOC-07 WS | AT-MSG-01..04 | No inconsistency found |
| Carryover / calendar / identity | TASK-003,005,009 | DOC-05 scheduler; DOC-06 tasks/calendar | AT-TASK-03,05,09 | No inconsistency found |
| Recurrence / unique constraint / scheduler | TASK-004 | DOC-05/DOC-06 task_instances uniqueness | AT-TASK-04 | No inconsistency found |
| AI / authorization / sources | AI-001..005 | DOC-05 AI boundary; DOC-06 briefing range; DOC-09 | AT-AI-01..05 | No inconsistency found; OD-003 gates activation |
| Admin scope / authorization / audit | AUTH-004,TASK-007 | DOC-06 admin_scopes/audit; DOC-07 admin status; DOC-09 | AT-AUTH-04, AT-TASK-07 | No inconsistency found |
| Windows / session storage / updates | WIN-001..003,AUTH-003,MSG-008 | DOC-05 trust boundary; DOC-08 UI; DOC-09 | AT-WIN-01..03, AT-AUTH-03 | No inconsistency found; OD-004 gates release |
