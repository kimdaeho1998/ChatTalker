# DOC-11 Acceptance Test Plan

## Execution rules
QA records environment, build/version, fixture, tester, result, evidence and defect link. `PASS` requires executed evidence, not document existence. Production data is never used. IDs map directly to traceability.

| Test IDs | Procedure and expected result |
|---|---|
| AT-AUTH-01 | Run approved local `chatalker-admin bootstrap` with interactive initial password and entered cryptographically secure one-time secret versus separately configured local-environment approved secret. Verify no public bootstrap API, no CLI argument/log/DB secret, one account plus audit commit atomically, rollback on failure, and database lock/constraint allows one concurrent winner only; second run fails closed without changing existing administrator. |
| AT-AUTH-02 | Create employee as scoped admin; verify public signup is absent, duplicate identity is `409`, and provision audit is immutable. |
| AT-AUTH-03 | Login with valid credentials returns 15-minute access and 7-day refresh lifetimes; invalid password and unknown login both return generic `401 AUTH_INVALID`. |
| AT-AUTH-04 | First login returns `PASSWORD_CHANGE_REQUIRED`; protected resource access is denied until successful password change. |
| AT-AUTH-05 | Verify expired access token and inactive/revoked session are rejected on REST. |
| AT-AUTH-06 | Refresh once; verify new refresh token works, old token is consumed, and server contains hashes only. |
| AT-AUTH-07 | Reuse a consumed refresh token; verify family/session revocation and audit event. |
| AT-AUTH-08 | Submit concurrent refresh requests for one token; verify exactly one succeeds and loser cannot create a second valid family. |
| AT-AUTH-09 | Logout then present prior refresh/access context; verify rejection and audit event. |
| AT-AUTH-10 | Deactivate account with active sessions; verify REST rejection, all session-family revocation, and audit event. |
| AT-AUTH-11 | Attempt WebSocket handshake/use with expired, revoked, or deactivated session; verify rejection or terminal close. |
| AT-AUTH-12 | Verify login, failure, password change, rotation, reuse, logout, revocation and deactivation audit events omit passwords and raw tokens. |
| AT-MSG-01..04 | Send direct/group message; alter membership; interrupt network/reconnect with cursor; assert committed-only ack and exactly-once UI dedupe. |
| AT-MSG-05..08, AT-ATT-01 | Attempt out-of-scope search/read/attachment download; assert R2 object is private and unscanned/failed object is unavailable; test receipt and notification behavior. |
| AT-AI-01..05 | Seed mixed priority unread content and unauthorized content; invoke first activation; validate rank/source links; force provider error; verify unread/task state unchanged; assert user-scoped cache. |
| AT-TASK-01..09 | Create/check task and timestamp; run carryover/repeat jobs twice against Korean-public-holiday/admin-day-off fixtures; validate lineage/unique instances/calendar/metrics; test admin scope and AI mutation denial. |
| AT-WIN-01..03, AT-OPS-01 | Install on supported Windows 10/11, test tray/disabled auto-start and reject tampered update; run 50 concurrent-user fixture and measure persisted-message delivery p95 <=1 second. |
| AT-NFR-01..10 | Verify TLS/RBAC, outage recovery, constraints, logging privacy, accessibility, version/platform matrix and release controls. NFR-004 cannot PASS until Owner performance targets exist. |

Blocked tests are not waived: they remain `BLOCKED` until corresponding Owner decision is approved. Regression set includes all mapped tests changed by API, DB, authorization, scheduler, or AI modifications.
