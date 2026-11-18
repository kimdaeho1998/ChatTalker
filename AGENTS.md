# SunBI Messenger Agent Instructions

## Scope and authority
Work only within approved requirements and preserve established contracts. Apply the minimum necessary change. Do not modify the legacy SunBI BOT frontend, backend, AI repositories, databases, environments, or deployment resources.

## Repository topology
This project is a single Monorepo rooted at `C:\Users\USER\Desktop\Chatalker` on the `main` branch. Keep desktop, backend, shared contracts, infrastructure, scripts, and documentation inside this repository. Do not create nested Git repositories, submodules, worktrees, or duplicate development folders.

## Delivery controls
- Implement only after an Owner-approved work order.
- Run relevant tests after implementation; never report PASS when tests were not run.
- Inspect Git status and changed files before handoff.
- Do not commit, push, deploy, access production databases, or change production configuration without explicit Owner approval.
- Do not hardcode credentials, passwords, or tokens.
- Record ambiguity as `OWNER_DECISION_REQUIRED`; do not silently choose a product policy.
