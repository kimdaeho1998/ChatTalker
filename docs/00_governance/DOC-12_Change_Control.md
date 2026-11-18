# DOC-12 Git / Deployment / Change Control

## Repository control
The approved repository is `C:\Users\USER\Desktop\Chatalker`. Keep HEAD, index, and working tree changes attributable and reviewable. Never overwrite or delete pre-existing content. Use small reviewed changes; inspect `git status`, diff, and tests before handoff.

It is a single Monorepo on `main`; `apps`, `packages`, `docs`, `infra`, `scripts`, and `.github` are governed by the root repository. Nested Git repositories, submodules, worktrees, and copied development repositories are prohibited.

## Change workflow
1. Link a requested change to requirement IDs and a work order.
2. Assess security, DB/API compatibility, migration, rollback, and test impact.
3. Obtain Owner approval if scope, external service, production configuration, or policy changes.
4. Implement and test only approved work.
5. Record evidence and update traceability. Owner alone authorizes commit, push, release, and deployment.

## Environment and release policy
Backend and PostgreSQL are independently deployed, but SM-R00 creates neither. Secrets live only in approved secret storage; no source control secrets. Release requires approved migration/rollback plan, vulnerability/dependency review, smoke tests, acceptance evidence, and Owner deployment authorization. Production DB access/change is prohibited in this phase.

## Version and compatibility policy
Pin and verify Tauri 2, React/TypeScript, Python 3.12, FastAPI, PostgreSQL, and OpenAI SDK/API compatibility during R01 discovery before coding. API changes require versioning or backward-compatible transition; database destructive migrations require approved backup and rollback.
