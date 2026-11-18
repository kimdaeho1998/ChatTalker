# DOC-01 Project Charter — SunBI Messenger

**Document status:** Draft for Owner approval | **Release:** SM-R00-R1 | **Project root:** `C:\Users\USER\Desktop\Chatalker`

## Purpose, scope, and success
SunBI Messenger is a Windows 10/11 installed internal messenger for headquarters staff. SM-R00 defines, but does not implement, a Tauri 2 / React TypeScript desktop client, FastAPI Python 3.12 backend, PostgreSQL data store, WebSocket real-time plane, and OpenAI API briefing integration. The product scope is: (1) direct/group messaging, (2) an access-controlled morning unread-message briefing, and (3) employee-check-based rule task journaling. Public registration, production changes, and any legacy SunBI BOT change are outside scope.

## Stakeholders and governance
Owner approves requirements, unresolved policy decisions, SM-R01 start, commits, pushes, and deployment. Administrator provisions accounts and authorized departmental visibility. Employee uses messaging and tasks. Technical Lead owns design conformance; Security Engineer owns access controls; QA Lead owns acceptance evidence. Document completion and Owner approval are separate states.

## Deliverables and boundaries
Deliverables are DOC-01 through DOC-12, traceability, decision log, risk register (in SM-R00), and SM-R01 implementation plan. No feature code, schema migration, service deployment, external integration, or credentials are created in SM-R00.

## Repository topology
The approved delivery topology is one Monorepo rooted at `C:\Users\USER\Desktop\Chatalker`: desktop client in `apps/desktop`, backend in `apps/backend`, shared contracts in `packages/contracts`, infrastructure in `infra`, automation in `scripts`/`.github`, and governing material in `docs`. It has one root Git repository and no nested repositories, submodules, worktrees, or duplicate project folders.

## Milestones and exit
R00 exit requires non-empty documents, unique requirement IDs, mapped acceptance tests, cross-contract review, and Owner review. R01 may begin only after Owner approves the decisions and work order listed in `SM-R01.md`.
