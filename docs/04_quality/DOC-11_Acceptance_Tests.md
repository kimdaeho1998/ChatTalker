# DOC-11 Acceptance Test Plan

## Execution rules
QA records environment, build/version, fixture, tester, result, evidence and defect link. `PASS` requires executed evidence, not document existence. Production data is never used. IDs map directly to traceability.

| Test IDs | Procedure and expected result |
|---|---|
| AT-AUTH-01..04 | Create account as admin; verify no signup; force password change; disable active user and socket; inspect immutable audit. Expected contracts AUTH-001..004. |
| AT-MSG-01..04 | Send direct/group message; alter membership; interrupt network/reconnect with cursor; assert committed-only ack and exactly-once UI dedupe. |
| AT-MSG-05..08, AT-ATT-01 | Attempt out-of-scope search/read/attachment download; assert R2 object is private and unscanned/failed object is unavailable; test receipt and notification behavior. |
| AT-AI-01..05 | Seed mixed priority unread content and unauthorized content; invoke first activation; validate rank/source links; force provider error; verify unread/task state unchanged; assert user-scoped cache. |
| AT-TASK-01..09 | Create/check task and timestamp; run carryover/repeat jobs twice against Korean-public-holiday/admin-day-off fixtures; validate lineage/unique instances/calendar/metrics; test admin scope and AI mutation denial. |
| AT-WIN-01..03, AT-OPS-01 | Install on supported Windows 10/11, test tray/disabled auto-start and reject tampered update; run 50 concurrent-user fixture and measure persisted-message delivery p95 <=1 second. |
| AT-NFR-01..10 | Verify TLS/RBAC, outage recovery, constraints, logging privacy, accessibility, version/platform matrix and release controls. NFR-004 cannot PASS until Owner performance targets exist. |

Blocked tests are not waived: they remain `BLOCKED` until corresponding Owner decision is approved. Regression set includes all mapped tests changed by API, DB, authorization, scheduler, or AI modifications.
