# DOC-07 REST / WebSocket API Contracts

## Common rules
HTTPS/WSS only. Bearer session token required except login; response `{code,message,correlation_id,data}`; validation errors are `400`, unauthenticated `401`, forbidden `403`, missing `404`, conflict/idempotency `409`, unavailable dependency `503`. Server rejects disabled/revoked accounts on every request and socket operation.

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

## WebSocket `GET /ws`
Handshake validates bearer token, account status/auth version. Client events: `subscribe`, `resume {after_cursor}`, `ping`. Server events: `message.created`, `message.read`, `conversation.updated`, `account.revoked`, `sync.page`, `error`. Each includes cursor/event ID where durable. On `account.revoked` server sends terminal event then closes. Clients deduplicate by entity/event ID; server retains no authorization bypass via cursor.
