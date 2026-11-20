import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  apiBaseUrl,
  changePassword,
  fetchHealth,
  login,
  logout as logoutRequest,
  refresh,
  type HealthResponse,
  type Session,
} from "./api";
import { SessionLifecycle } from "./sessionLifecycle";

type HealthState =
  | { kind: "loading" }
  | { kind: "success"; data: HealthResponse }
  | { kind: "error"; message: string };

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [passwordChangeToken, setPasswordChangeToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const lifecycle = useRef<SessionLifecycle | null>(null);

  if (!lifecycle.current) {
    lifecycle.current = new SessionLifecycle(
      {
        store: (token) => invoke("store_refresh_token", { token }),
        load: () => invoke<string | null>("load_refresh_token"),
        remove: () => invoke("delete_refresh_token"),
      },
      {
        refresh: async (token) => (await refresh(token)).data,
        logout: logoutRequest,
      },
      setAccessToken,
    );
  }

  const signIn = async () => {
    setError(null);
    setSessionExpired(false);
    const generation = lifecycle.current!.beginAuthentication();
    try {
      const result = await login(loginName, password);
      if (result.code === "PASSWORD_CHANGE_REQUIRED") {
        setPasswordChangeToken((result.data as { password_change_token: string }).password_change_token);
        return;
      }
      await lifecycle.current!.establish(result.data as Session, generation);
    } catch {
      setError("Authentication failed.");
    }
  };

  const completePasswordChange = async () => {
    if (!passwordChangeToken) return;
    setError(null);
    const generation = lifecycle.current!.beginAuthentication();
    try {
      const result = await changePassword(password, newPassword, passwordChangeToken);
      setPasswordChangeToken(null);
      await lifecycle.current!.establish(result.data, generation);
    } catch {
      setError("Password change failed.");
    }
  };

  const signOut = async () => {
    try {
      const result = await lifecycle.current!.logout();
      setPasswordChangeToken(null);
      setSessionExpired(result === "server_unavailable");
    } catch {
      setPasswordChangeToken(null);
      setError("Signed out locally, but credential cleanup failed.");
    }
  };

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
    void lifecycle.current!.restore().catch(() => {
      setSessionExpired(true);
      setError("Session expired. Please sign in again.");
    });
  }, []);

  return (
    <main className="app-shell">
      <section className="card">
        <p className="eyebrow">SM-R01-A · Development Foundation</p>
        <h1>Chatalker</h1>
        {accessToken ? (
          <>
            <p>Authenticated main shell.</p>
            <button type="button" onClick={() => void signOut()}>Sign out</button>
          </>
        ) : passwordChangeToken ? (
          <>
            <p>Change your password before continuing.</p>
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New password" />
            <button type="button" onClick={() => void completePasswordChange()}>Change password</button>
          </>
        ) : (
          <>
            <p>{sessionExpired ? "Session expired. Sign in to continue." : "Sign in to Chatalker."}</p>
            <input value={loginName} onChange={(e) => setLoginName(e.target.value)} placeholder="Login" />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
            <button type="button" onClick={() => void signIn()}>Sign in</button>
          </>
        )}
        {error && <p role="alert">{error}</p>}
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
