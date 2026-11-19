# DOC-07 REST / WebSocket API Contracts

## Common rules
HTTPS/WSS only. Bearer access token is required except login and refresh; response `{code,message,correlation_id,data}`; validation errors are `400`, unauthenticated `401`, forbidden `403`, missing `404`, conflict/idempotency `409`, unavailable dependency `503`. Authentication failures use generic `401 AUTH_INVALID` and never disclose whether an account exists. Access tokens expire after 15 minutes; refresh tokens expire after 7 days. The server never persists a raw refresh token and validates active account, session, auth version, token family and expiration on API and WebSocket operations. Public bootstrap API is disabled.

| Operation | Input → output / authorization |
|---|---|
| `POST /auth/login` | login/password → `PASSWORD_CHANGE_REQUIRED` or session; rate-limit and generic auth failure. |
| `POST /auth/password` | old/new → session; current authenticated user only. |
| `POST /admin/accounts`, `PATCH /admin/accounts/{id}` | staff/status/role/scope → account/audit ID; authorized admin only. |
| `GET/POST /conversations`, `POST /conversations/{id}/messages` | membership/message/idempotency key → durable message; participant only. |
| `GET /sync?after=` | cursor → ordered events/page; current authorized content only. |
| `GET /messages/search`, `POST /messages/{id}/read` | query or explicit receipt → scoped results/state. |
| `POST /attachments`, `GET /attachments/{id}` | private R2 upload/retrieval flow; server verifies conversation authorization and `scan_status=passed`; unscanned/failed is unavailable. |
| `POST /briefings/morning` | local date/timezone → `{status,items:[message_id,summary,priority]}` or fallback source IDs; no read/task mutation. |
| `POST /tasks`, `POST /tasks/{id}/check`, `GET /tasks/metrics` | owned task/check/filter → state/metrics; owner only. |
| `GET /admin/task-status` | chief admin may query company scope; standard admin only delegated departments; sensitive results are audited. |

## Detailed authentication contract

| Operation | Request / successful response | Authentication, authorization and error contract |
|---|---|---|
| `chatalker-admin bootstrap` (local CLI) | Interactive login/display name, initial password and entered one-time secret; separately loaded local-environment approved secret → first administrator account/audit ID | No public API exists. Approved operator only; no secret appears in command-line arguments, logs or DB. CLI performs cryptographically secure secret comparison, discards local secret material after success, and invokes one atomic PostgreSQL transaction with lock/constraint control. Existing administrator/bootstrap state, failed comparison or concurrent loser fails closed; rollback leaves no account/audit partial state. |
| `POST /admin/accounts` | Staff identity, department, role, initial credential delivery reference → account ID/audit ID | Server resolves current caller authority. `chief_admin` may create company-wide accounts; `standard_admin` may create only `employee` accounts in a currently granted department; `employee` is denied. A standard administrator cannot create any administrator. Duplicate login is `409`; unauthorized or out-of-scope caller is `403`; no public counterpart exists. |
| `POST /auth/login` | `login`, `password` → `PASSWORD_CHANGE_REQUIRED` or `{access_token, access_expires_in:900, refresh_token, refresh_expires_in:604800, session_id}` | Publicly callable and rate-limited. Unknown login, invalid password, disabled account and revoked state return generic `401 AUTH_INVALID`; normal tokens never issue before required password change. |
| `POST /auth/refresh` | Refresh token → rotated access/refresh pair and session metadata | One atomic use only. Expired, revoked, unknown or reused token returns `401 AUTH_INVALID`; detected reuse or losing concurrent refresh revokes its family and active sessions and audits the event. |
| `POST /auth/logout` | Current session/refresh context → revocation confirmation | Authenticated current session only; successful revocation is idempotent. Subsequent access or refresh is rejected. |
| `POST /auth/password` | Current password, new password → normal token pair after required change or password-change confirmation | Current authenticated or change-required context only. Invalid old/new policy result is safe `400`; password is never logged. |
| `PATCH /admin/accounts/{id}` | Status, role, department or scope change → account/audit ID | Server enforces the authorization matrix. `chief_admin` may manage company-wide accounts and grant/revoke `standard_admin` authority or department scopes, except their own role/scope. `standard_admin` may change status/department only for `employee` targets within currently granted departments and cannot alter any administrator role/scope. `employee` is denied. Deactivation, role/scope revocation, and authority changes revoke affected sessions/token families and terminate sockets transactionally; unauthorized or out-of-scope is `403`, missing is `404`. |
| `POST /admin/accounts/{id}/sessions/revoke` | Optional target session/family → audit/revocation confirmation | `chief_admin` may revoke company-wide; `standard_admin` may revoke only an `employee` target in a currently granted department; `employee` is denied. Selected or all target session families are revoked without exposing raw tokens. |

## WebSocket `GET /ws`
Handshake validates bearer access token, active session, account status/auth version and expiration. Client events: `subscribe`, `resume {after_cursor}`, `ping`. Server events: `message.created`, `message.read`, `conversation.updated`, `account.revoked`, `sync.page`, `error`. Each includes cursor/event ID where durable. On session revoke, account deactivation, or token invalidation server sends terminal `account.revoked` where safe then closes. Invalid handshakes are rejected without account-existence disclosure. Clients deduplicate by entity/event ID; server retains no authorization bypass via cursor.
