# DOC-02 Software Requirements Specification

## System context
The authenticated Windows desktop application communicates over TLS with a FastAPI API and authenticated WebSocket gateway. PostgreSQL holds durable identities, messages, tasks, read state, audit records, and briefing metadata. An AI worker may receive only authorized message excerpts after Owner approval. The server, not client, enforces authorization and task automation.

## Requirement catalog
Each row defines purpose/condition, input/output, normal and exception behavior, and verifiable acceptance criterion (AC).

| ID / priority | Requirement contract | AC |
|---|---|---|
| AUTH-001 P0 | Only an authorized administrator provisions a staff identity, department, role and safely delivered initial credential; public registration is absent. RBAC roles are `chief_admin`, `standard_admin`, and `employee`. A chief administrator has company-wide account authority; a standard administrator may provision or manage only employee accounts in an explicitly granted department and may never administer administrator roles or scopes. First administrator bootstrap is the separate ONE_TIME_LOCAL_CLI, never a public API: approved operator enters a cryptographically random one-time secret and initial password interactively; CLI compares it with a separately supplied local-environment approved secret, never a command-line argument. PostgreSQL transaction/lock/constraint permits one winner, writes account/audit atomically, then consumes the bootstrap state; duplicate, concurrent, or repeat execution fails closed. | Creation succeeds once; public endpoint is absent; bootstrap cannot recur; no secret is logged/stored in DB; first account and audit commit atomically. The server denies cross-department, self-authority, and administrator-authority changes outside the role/scope matrix. |
| AUTH-002 P0 | Login accepts login/password without revealing account existence. Argon2id verifies credentials. First credential login returns `PASSWORD_CHANGE_REQUIRED` and no normal access token; authenticated password change then issues a 15-minute access token and a 7-day refresh token. Reject invalid, disabled, expired, or policy-invalid inputs with generic safe errors. | First session cannot access protected data before change; valid post-change login returns the specified token lifetimes. |
| AUTH-003 P0 | Refresh tokens are stored only as hashes in PostgreSQL and rotate atomically on use. Reuse or concurrent double-use revokes the entire token family and active sessions. Logout, explicit session revocation, and account deactivation revoke applicable sessions; status/auth-version is validated for every API and WebSocket operation. | Used refresh token cannot be reused; disabled user cannot call API or remain connected; stale access tokens are rejected by session validation. |
| AUTH-004 P0 | Account/role/department/session changes and authentication security events are immutable audit events with actor, target, timestamp, before/after where applicable, correlation ID and safe result code. Role and department-scope grants, revocations, and denied authority changes are audited. | Authorized auditor can query required events; audit records never contain passwords or raw tokens. |
| MSG-001 P0 | Authorized participant sends 1:1 message; input conversation/text, output durable message ID/timestamp. Reject nonparticipant/invalid text. | Recipient obtains identical persisted message after sync. |
| MSG-002 P0 | Authorized members create/use group conversation; membership changes are audited and govern delivery. | Removed member cannot read new group content. |
| MSG-003 P0 | Persist message, edit/deletion policy pending Owner decision, sender/time/conversation metadata. Failure returns no false success. | Ack only after durable write. |
| MSG-004 P0 | WebSocket reconnect sends cursor; output ordered missed authorized events. Expired/invalid cursor falls back paginated REST sync. | Disconnect/reconnect produces no duplicate/lost message IDs. |
| MSG-005 P1 | Search authorized stored messages by approved query/scope; output only permitted results. | Cross-conversation result is never exposed. |
| MSG-006 P1 | Read state is explicit user action/open event with per-user message pointer/receipt. | Sender sees recipient read status only when allowed. |
| MSG-007 P1 | File transfer uses private Cloudflare R2; server issues only authorized access and publishes an attachment after malware scan passes. Reject oversize/type/scan/policy failure. | Download authorization equals conversation authorization; unscanned/failed objects are unavailable. |
| MSG-008 P1 | Tauri 2 Windows notification deep-links to an authorized target and respects OS/user policy. | Notification opens authorized target; policy-disabled behavior is suppressed. |
| AI-001 P0 | First morning app activation selects user's unread authorized messages; input user/time zone/cursor, output briefing or fallback. | Only messages user may read are included. |
| AI-002 P0 | Rank mentions, important notices, task requests and deadlines before ordinary messages using transparent source links. | Test data ranks priority classes first and each item links source. |
| AI-003 P0 | AI output never marks messages read or changes task completion. | Post-briefing unread/task state is unchanged. |
| AI-004 P0 | AI failure/timeout/policy denial returns original unread authorized list and status. | UI remains usable with source list. |
| AI-005 P1 | Cache/deduplicate same user, message-range, prompt-version request within approved TTL; no cross-user cache exposure. | Repeated range avoids duplicate analysis and access test passes. |
| TASK-001 P0 | Employee creates own task with title, due date/time optional, planned date, and metadata; output task ID. | User cannot create task for another user absent approved delegation. |
| TASK-002 P0 | Employee marks task complete/incomplete; output state and completion timestamp/audit. | Completion timestamp is server-recorded and changes only on state transition. |
| TASK-003 P0 | Scheduled job rolls incomplete eligible task to next business day; preserve root task ID and original created date. | Carryover is linked and does not alter origin. |
| TASK-004 P0 | Weekly recurrence creates task for scheduled business date; unique recurrence-rule/date/assignee prevents duplicate. | Job rerun yields one instance only. |
| TASK-005 P0 | Calendar/holiday policy determines business dates; missing policy/calendar fails safely and alerts administrator. | No unreviewed date is generated when source unavailable. |
| TASK-006 P0 | Calculate completion rate, due-date compliance, and carryover count from employee checked state only. | Fixture formulas match displayed metrics. |
| TASK-007 P0 | Authorized admin views only delegated employee/department task aggregates/details. | Unauthorized department query is denied/filtered. |
| TASK-008 P0 | AI cannot create, complete, reopen, or infer task state. | AI service credentials lack task mutation scope. |
| WIN-001 P0 | Deliver an installable Windows 10/11 desktop client; input approved installer, output successful supported-OS installation or clear incompatibility error. | Clean supported Windows 10/11 test installation launches the signed client. |
| WIN-002 P1 | Provide Tauri 2 system-tray presence and approved automatic start; input user/OS setting, output visible tray state and startup behavior. | Tray actions require no unauthorized access; disabled auto-start does not launch on sign-in. |
| WIN-003 P0 | Verify signed automatic update metadata/artifacts before install; reject unsigned or invalid signatures. | Tampered update is rejected and current app remains usable. |
| ATT-001 P0 | Store attachments privately in Cloudflare R2 and require malware scan pass before availability. | Unauthorized or unscanned attachment retrieval is denied. |
| TASK-009 P1 | Show employee task calendar using Korean public holidays and administrator-designated days off; output business/non-business status and planned tasks. | Calendar fixture renders approved holiday/admin-day data and scheduler uses same date. |
| OPS-001 P0 | Support initial 50 concurrent authenticated users with persisted-message delivery p95 <=1 second under Owner-approved load fixture. | Measured test meets target; otherwise requirement is not PASS. |

## Global validation
Inputs are schema validated server-side; all timestamps are UTC with user-local display; errors are stable machine codes plus safe UI text. API output excludes credentials and unauthorized metadata. See DOC-03 for flows, DOC-04 for quality, and DOC-11 for test IDs.
