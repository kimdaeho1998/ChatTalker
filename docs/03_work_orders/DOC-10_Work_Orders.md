# DOC-10 Development Work Orders

No work order authorizes implementation until Owner approval.

| ID | Deliverable / dependencies / evidence |
|---|---|
| WO-R01-01 | Validate toolchain versions and Windows compatibility; dependency lock evidence; resolves version gate. |
| WO-R01-02 | Implement identity/session/RBAC/audit vertical slice; AUTH tests and security review. OD-002 is accepted in SM-R01-B-R0: 15-minute access, 7-day refresh, hash-only PostgreSQL refresh storage, rotation/reuse detection, session revocation and REST/WSS validation. OD-005 is accepted in SM-R01-B-R0-F1: first administrator is ONE_TIME_LOCAL_CLI with separate local-environment approved secret, interactive inputs, atomic PostgreSQL single-winner control, fail-closed reexecution and audit. |
| WO-R01-03 | Implement durable conversations, messages, sync and receipts; migration + disconnect/reconnect tests. |
| WO-R01-04 | Implement task model, Korean-holiday/admin-day-off calendar adapter, recurrence/carryover idempotency and metrics; ADR-004 accepted. |
| WO-R01-05 | Implement briefing authorization/fallback and approved AI gateway; ADR-007 accepted, external activation needs OD-003. |
| WO-R01-06 | Implement Windows shell notifications/tray/auto-start/update and private attachment transfer; ADR-005/008 accepted, release configuration needs OD-001/OD-004. |
| WO-R01-07 | Execute integration/security/acceptance evidence and release-readiness review; needs all preceding work. |

Each work order requires linked requirements, design/API/DB impact, tests, rollback/migration plan, changed-file list and Owner approval.

All approved work is performed in the single root Monorepo. Work orders must not create nested repositories, submodules, worktrees, or copied project roots.
