# DOC-03 Functional Requirements Document

## Authentication flows
Admin submits a staff identity record to `AUTH-001`; server checks administrative scope, creates an active account in change-required state, and writes an audit event. First login (`AUTH-002`) issues no normal access token until password change completes. Status disable (`AUTH-003`) increments auth version/revokes active sessions and closes active sockets; all subsequent protected requests are denied. Every authority change uses `AUTH-004` audit fields.

## Messaging flows
Client posts a message then receives durable acknowledgement (`MSG-001`, `MSG-003`), followed by WebSocket delivery to current authorized participants. Group membership (`MSG-002`) is checked on both history/read and live delivery. A reconnect presents last durable event cursor (`MSG-004`); server returns ordered authorized events or requires REST pagination. Search, receipts, attachments and OS integration follow `MSG-005`–`MSG-008`; attachment content storage and retention remain pending Owner policy.

## Morning briefing flows
On first local-day activation, client requests briefing. Server resolves the user/timezone and unread authorized range, ranks message signals, creates source-linked response, and records non-content operational metadata. AI only receives the filtered authorized range. `AI-003` forbids state mutation. If timeout, provider rejection, or unavailable service occurs, `AI-004` returns the source unread list. Same user/range/prompt version may reuse an access-controlled cache (`AI-005`).

## Task flows
Employee creates and checks only their tasks (`TASK-001`, `TASK-002`). A server scheduler consults approved calendar rules and creates a new carryover instance linked to `root_task_id`, retaining original creation date (`TASK-003`). Recurrence is idempotent through a unique tuple (`TASK-004`). Missing calendar data produces an operational error (`TASK-005`), never guessed dates. Metrics are a server calculation over check history (`TASK-006`); administrator filter scope is enforced at query time (`TASK-007`). AI holds read-only briefing scope only (`TASK-008`).

## Cross-reference
All requirements use the inputs, outputs, exceptions, security constraints, data rules and acceptance evidence listed in DOC-02 and matrix. API messages are specified in DOC-07; UI recovery states in DOC-08.

## R2 approved-policy clarification
Attachments are private Cloudflare R2 objects and remain unavailable until the malware-scan gate passes; retention and scanner product are OPEN. Korean public holidays plus administrator-designated days off are the shared calendar input for carryover, recurrence, and task-calendar display. Chief administrators operate company-wide account management; standard administrators operate delegated departments. The briefing filter is unread messages only in work chat rooms accessible to the requester, with minimum necessary transfer and source links. Notification, tray, signed-update verification, Windows installation, and auto-start have separate acceptance contracts in `MSG-008`, `WIN-001` through `WIN-003`. Session expiry, AI retention/notice, attachment retention/scanner product, and update distribution/signing operations remain implementation gates.
