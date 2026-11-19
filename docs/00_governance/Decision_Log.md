# Architecture Decision Record and Owner Decision Log

| ID | Decision / status | Rationale / impact | Owner action |
|---|---|---|---|
| ADR-001 | Accepted: separate desktop, API, DB, WebSocket planes | Limits blast radius and supports independent backend/DB operation | Recorded |
| ADR-002 | Accepted: PostgreSQL is source of truth; WebSocket is delivery channel | Enables reconnect sync and auditability | Recorded |
| ADR-003 | Accepted: task completion is employee-check only | AI must not infer or mutate completion | Recorded |
| ADR-004 | Accepted: Korean public holidays plus administrator-designated non-working days are the business calendar | Scheduler uses approved `business_calendar`; no inferred dates | Calendar data owner/entry workflow remains OPEN |
| ADR-005 | Accepted: private Cloudflare R2 attachments, access control, malware scanning | Attachment object access is authorized through server; scan must pass before availability | Retention period and scanner product remain OPEN |
| ADR-006 | Accepted: admin-issued accounts, Argon2id, first-password change, server-side session revocation | No public signup; disabled/revoked account loses REST/WSS access | Token/session detail is governed by OD-002 |
| ADR-007 | Accepted: AI analyses only unread messages in work chat rooms accessible to the requesting user, with minimum necessary data and source links | Server filters/ranks authorized source set; summary cannot mutate read/task state | AI retention and external-transmission notice remain OPEN |
| ADR-008 | Accepted: Tauri 2 Windows notifications, system tray, and signature-verified automatic updates | OS integration is policy-gated and signed update verification is mandatory | Distribution/signing operations remain OPEN |
| ADR-009 | Accepted: chief administrator manages company-wide accounts; standard administrator manages delegated departments | Server RBAC and audit enforce scope | Delegation administration workflow remains OPEN |
| ADR-010 | Accepted: initial target is 50 concurrent users and message-delivery p95 <=1 second | Load test must measure persisted-message to authorized-client delivery | Test fixture, observation window, and production SLO remain OPEN |
| OD-001 | OPEN: attachment retention period and malware-scanning product | Blocks final attachment operational implementation/release | Owner decision required |
| OD-002 | **Accepted by Owner in SM-R01-B-R0:** Access Token TTL 15 minutes; Refresh Token TTL 7 days; PostgreSQL session store; refresh rotation, reuse detection and hash-only refresh storage are mandatory | Admin-only provisioning; no public registration; first-login password change; deactivate revokes all sessions; API/WSS validate active session; authentication audit is mandatory | Authentication token/session contracts are unblocked; separate bootstrap controls are governed by OD-005. |
| OD-003 | OPEN: AI data retention and external-transmission notice | Blocks external AI activation/release | Owner decision required |
| OD-004 | OPEN: Windows update distribution and signing operations | Blocks automatic-update release configuration | Owner decision required |
| OD-005 | **Accepted by Owner in SM-R01-B-R0-F1:** first administrator uses ONE_TIME_LOCAL_CLI; public bootstrap API is disabled | Approved operator executes local CLI, enters one-time secret and initial admin password interactively; separately sourced local-environment approved secret is compared, never logged or passed as an argument, and is discarded on success | PostgreSQL transaction/lock/constraint provides one winner; reexecution fails closed; account plus audit commit atomically |
