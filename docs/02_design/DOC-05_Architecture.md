# DOC-05 System Architecture Design

## Logical components
`Tauri 2 shell → React/TypeScript UI → HTTPS REST + WSS → FastAPI` is the application path. FastAPI hosts authentication, authorization, conversations, tasks, reporting and briefing orchestration. PostgreSQL is the transactional source of truth. A background scheduler/worker performs recurrence/carryover serially/idempotently. AI gateway is an optional, policy-gated outbound component; it uses least-privilege filtered content and returns source-linked summaries. Private R2 attachment storage and a malware-scan availability gate are approved; scanner product and retention are OPEN under OD-001.

## Trust boundaries and flow
Desktop tokens are held in OS-backed secure storage where supported, never application source. API validates token/version/status for REST and WebSocket handshake; authorization is re-evaluated on sensitive operations. Message write transaction commits message plus delivery event, then broadcasts. Client stores last server cursor and syncs after reconnect. The server calculates unread status, briefing selection, task metrics, and admin scope; UI never authoritatively decides them.

## Failure behavior
Client uses bounded reconnect/backoff and displays offline state. Sync is idempotent by durable IDs/cursors. AI errors return source unread items. Scheduler takes transactional advisory/row lock and emits operational alert on calendar-policy failure. DB/API outages return retriable safe errors; no local fabricated acknowledgement.

## Technology validation gate
Before R01, verify current supported versions and Windows toolchain compatibility for Tauri 2/WebView2, React/TypeScript build, Rust, Python 3.12/FastAPI, PostgreSQL driver, WebSocket library and OpenAI SDK. Results must be recorded; no unverified version is a production commitment.

## Source topology
One root repository contains the planned desktop client (`apps/desktop`), FastAPI service (`apps/backend`), shared contracts (`packages/contracts`), infrastructure (`infra`), automation (`scripts`, `.github`), and specifications (`docs`). This is a delivery boundary, not permission to implement components during SM-R00.

## R2 approved-policy architecture
The scheduler reads the shared Korean-public-holiday and administrator-day-off calendar. Private Cloudflare R2 attachment objects are reached only through the authorized backend and become retrievable only after a passed malware scan. Briefing orchestration filters to the requesting user's unread, accessible work-chat messages and sends only minimum necessary content; every output retains source message IDs. Tauri verifies update signatures before installation. Session expiry, AI retention/notice, scanner product/retention, and update distribution/signing operation are deliberately external configuration gates, not inferred design decisions.
