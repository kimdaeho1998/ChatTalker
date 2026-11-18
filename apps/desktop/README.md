# Chatalker Desktop

The SM-R01-A desktop foundation is a Tauri 2, React, TypeScript, and Vite application. It exposes only a development start screen and backend `/health` indicator; authentication, messaging, tasks, and AI are intentionally absent.

Copy `.env.example` to a local `.env` only when overriding `VITE_API_BASE_URL`. Do not commit that file. With Node/npm and Rust installed, run `npm run tauri dev` from this directory.
