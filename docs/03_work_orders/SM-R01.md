# SM-R01 Implementation Plan

## Proposed implementation sequence
1. Capture Owner decisions ADR-004 through ADR-009 and verify stack compatibility.
2. Establish secure local development configuration and test harness without production access.
3. Deliver authentication/RBAC/audit and the data migration baseline.
4. Deliver messaging durability, membership, WebSocket replay and read state.
5. Deliver employee task creation/checking, calendar-driven idempotent carryover/recurrence and metrics.
6. Deliver authorized briefing with AI policy gate and mandatory source-list fallback.
7. Deliver approved attachments/Windows integrations, hardening, acceptance and release review.

## Entry criteria
Owner approves this work order; verified dependency matrix; named non-production environments; secret-management plan; migration/backup/rollback plan; test data strategy; no unresolved contract conflict; and a measured 50-user/p95 delivery test plan. Final production authentication configuration is blocked by session-expiry policy (OD-002). External AI activation is blocked by retention/notice policy (OD-003); attachment release is blocked by OD-001; automatic-update release configuration is blocked by OD-004. **Status:** NOT AUTHORIZED TO START. R01 scope excludes any unapproved feature.

## Repository execution boundary
R01 work, if separately approved, uses the root Monorepo: `apps/desktop`, `apps/backend`, `packages/contracts`, `infra`, `scripts`, `.github`, and `docs`. It must not create a second repository, nested Git repository, submodule, worktree, or copied development folder.
