import { useEffect, useState } from "react";
import { apiBaseUrl, fetchHealth, type HealthResponse } from "./api";

type HealthState =
  | { kind: "loading" }
  | { kind: "success"; data: HealthResponse }
  | { kind: "error"; message: string };

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  const refreshHealth = async () => {
    setHealth({ kind: "loading" });
    try {
      setHealth({ kind: "success", data: await fetchHealth() });
    } catch (error) {
      setHealth({
        kind: "error",
        message: error instanceof Error ? error.message : "Unknown health check error",
      });
    }
  };

  useEffect(() => {
    void refreshHealth();
  }, []);

  return (
    <main className="app-shell">
      <section className="card">
        <p className="eyebrow">SM-R01-A · Development Foundation</p>
        <h1>Chatalker</h1>
        <p>Windows internal messenger foundation. Authentication and messaging are not enabled.</p>
        <dl>
          <dt>API base URL</dt>
          <dd>{apiBaseUrl}</dd>
          <dt>Backend health</dt>
          <dd>
            {health.kind === "loading" && "Checking…"}
            {health.kind === "success" && `${health.data.status} (${health.data.database}; database is not checked)`}
            {health.kind === "error" && `Unavailable: ${health.message}`}
          </dd>
        </dl>
        <button type="button" onClick={() => void refreshHealth()}>
          Retry health check
        </button>
      </section>
    </main>
  );
}
