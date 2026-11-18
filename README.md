# SunBI Messenger

Windows 10/11 installed internal messenger, designed under the SM-R00 baseline. Implementation is not authorized by this repository initialization.

## Monorepo layout

- `apps/desktop` - planned Tauri 2 and React TypeScript client
- `apps/backend` - planned FastAPI backend
- `packages/contracts` - planned shared API and domain contracts
- `docs` - approved requirements, design, quality, and governance documents
- `infra/docker`, `infra/render` - planned deployment definitions
- `scripts` - approved repository automation only
- `.github/workflows` - planned CI workflows

One Git repository at the project root owns all paths. No submodules, nested repositories, worktrees, feature code, dependencies, database resources, commits, pushes, or deployments are created by this initialization.
