# DOC-09 Security & Authorization Policy

## Roles and authorization
Employee: own profile/session, member conversations, own tasks/metrics, own briefing. Administrator: account provisioning/status and explicitly delegated departments only; no implicit unrestricted message-content access. Service scheduler: task automation only. AI gateway: filtered briefing input and summary output only; no account, message mutation, task mutation, or unrestricted DB credentials. Enforce access in API/DB query scope, never only UI.

## Authentication and session
No public registration. Password hashing uses Argon2id and first login forces password change; server-side revocation is required. Complexity, history, lockout, MFA/SSO and session expiry remain OPEN under OD-002. Tokens have audience, expiration, rotation/revocation semantics; account disable increments session auth version and terminates WebSockets. Never log credentials/tokens.

## Data protection, audit, and AI
TLS protects in transit; encryption-at-rest/key management and retention require operations approval. Audit account/permission changes and sensitive administrative queries with actor/time/target/result. Briefing selection rechecks user authorization; summaries contain source message IDs and deep links. Provider selection, data minimization, retention, region, model and spend ceiling are blocked until ADR-007. AI cannot change read or task state.

## Threat controls
Validate schemas and file metadata; parameterize queries; constrain WebSocket origin/rate/message size; use CSP and Tauri least-privilege capabilities; rate-limit login/search/briefing; patch dependencies; use correlation IDs without secret content. Attachment malware scanning is required; scanner product and retention are OPEN under OD-001. Security acceptance maps to AT-AUTH-03/04, AT-MSG-05/07, AT-AI-01/03/05, AT-TASK-07/08 and AT-NFR-01/05/06.

## R2 approved-policy clarification
Passwords use Argon2id and first login forces a password change; server-side revocation invalidates REST and WebSocket sessions. Chief administrators have company account-management scope; standard administrators have explicitly delegated-department scope, with audit records for authority changes and sensitive queries. AI may receive only minimum necessary unread messages in accessible work rooms and must return source linkage; retention and external-transfer notice are OPEN. Private R2 objects require backend authorization and passed malware scanning. Tauri automatic update verification requires valid signatures. Session expiry, scanner product/retention, and update distribution/signing operations remain OPEN.
