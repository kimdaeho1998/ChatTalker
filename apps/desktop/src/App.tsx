import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { apiBaseUrl, AuthApiError, changePassword, fetchHealth, login, logout as logoutRequest, refresh, type HealthResponse, type Session } from "./api";
import { createAccount, getAccount, getAccounts, getCurrentAccount, getDepartments, getRoles, updateAccount, type Account, type CurrentAccount, type Department, type Role } from "./adminApi";
import { SessionLifecycle } from "./sessionLifecycle";

type HealthState = { kind: "loading" } | { kind: "success"; data: HealthResponse } | { kind: "error"; message: string };
type View = "home" | "accounts" | "create" | "detail";

const errorMessage = (error: unknown) => {
  if (error instanceof AuthApiError) {
    return ({ 400: "The request was invalid.", 401: "Your session has expired.", 403: "You do not have permission for this action.", 404: "The requested account was not found.", 409: "This conflicts with an existing account." }[error.status] ?? "The server could not complete the request.");
  }
  return "The network request failed. Please try again.";
};

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [passwordChangeToken, setPasswordChangeToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [currentAccount, setCurrentAccount] = useState<CurrentAccount | null>(null);
  const [view, setView] = useState<View>("home");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selected, setSelected] = useState<Account | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "active" | "disabled">("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [newLogin, setNewLogin] = useState("");
  const [newInitialPassword, setNewInitialPassword] = useState("");
  const [newDepartment, setNewDepartment] = useState("");
  const [newRole, setNewRole] = useState<Role["code"]>("employee");
  const lifecycle = useRef<SessionLifecycle | null>(null);

  if (!lifecycle.current) {
    lifecycle.current = new SessionLifecycle(
      { store: (token) => invoke("store_refresh_token", { token }), load: () => invoke<string | null>("load_refresh_token"), remove: () => invoke("delete_refresh_token") },
      { refresh: async (token) => (await refresh(token)).data, logout: logoutRequest }, setAccessToken,
    );
  }
  const authorizedFetch = lifecycle.current.authorizedFetch.bind(lifecycle.current);
  const isAdmin = currentAccount?.role_code === "chief_admin" || currentAccount?.role_code === "standard_admin";
  const canManageRoles = currentAccount?.role_code === "chief_admin";

  const refreshHealth = async () => { setHealth({ kind: "loading" }); try { setHealth({ kind: "success", data: await fetchHealth() }); } catch (caught) { setHealth({ kind: "error", message: caught instanceof Error ? caught.message : "Unknown health check error" }); } };
  const loadCurrentAccount = async () => { try { setCurrentAccount(await getCurrentAccount(authorizedFetch)); } catch (caught) { setCurrentAccount(null); setError(errorMessage(caught)); } };
  const loadAdminMetadata = async () => { try { const [nextDepartments, nextRoles] = await Promise.all([getDepartments(authorizedFetch), getRoles(authorizedFetch)]); setDepartments(nextDepartments); setRoles(nextRoles); } catch (caught) { setError(errorMessage(caught)); } };
  const loadAccounts = async (nextOffset = offset) => {
    setLoading(true); setError(null);
    try { const page = await getAccounts(authorizedFetch, { limit: 20, offset: nextOffset, search: search || undefined, status: statusFilter || undefined, department_id: departmentFilter || undefined }); setAccounts(page.items); setTotal(page.total); setOffset(page.offset); }
    catch (caught) { setError(errorMessage(caught)); } finally { setLoading(false); }
  };
  const openAccounts = async () => { setView("accounts"); await Promise.all([loadAdminMetadata(), loadAccounts(0)]); };
  const openDetail = async (accountId: string) => { setLoading(true); setError(null); try { setSelected(await getAccount(authorizedFetch, accountId)); setView("detail"); } catch (caught) { setError(errorMessage(caught)); } finally { setLoading(false); } };
  const signIn = async () => {
    setError(null); setSessionExpired(false); const generation = lifecycle.current!.beginAuthentication();
    try { const result = await login(loginName, password); if (result.code === "PASSWORD_CHANGE_REQUIRED") { setPasswordChangeToken((result.data as { password_change_token: string }).password_change_token); return; } await lifecycle.current!.establish(result.data as Session, generation); } catch { setError("Authentication failed."); }
  };
  const completePasswordChange = async () => { if (!passwordChangeToken) return; setError(null); const generation = lifecycle.current!.beginAuthentication(); try { const result = await changePassword(password, newPassword, passwordChangeToken); setPasswordChangeToken(null); setNewPassword(""); await lifecycle.current!.establish(result.data, generation); } catch { setError("Password change failed."); } };
  const signOut = async () => { try { const result = await lifecycle.current!.logout(); setPasswordChangeToken(null); setCurrentAccount(null); setView("home"); setSessionExpired(result === "server_unavailable"); } catch { setPasswordChangeToken(null); setCurrentAccount(null); setError("Signed out locally, but credential cleanup failed."); } };
  const submitCreate = async () => { setError(null); try { await createAccount(authorizedFetch, { login: newLogin, initial_password: newInitialPassword, role_code: newRole, department_id: newDepartment || undefined }); setNewLogin(""); setNewInitialPassword(""); setNewDepartment(""); setNewRole("employee"); await openAccounts(); } catch (caught) { setError(errorMessage(caught)); } };
  const saveSelected = async (change: { status?: "active" | "disabled"; role_code?: Role["code"]; department_id?: string }) => {
    if (!selected) return;
    if (change.status === "disabled" && !window.confirm(`Deactivate ${selected.login}? This revokes their sessions.`)) return;
    setError(null); try { await updateAccount(authorizedFetch, selected.account_id, change); await openDetail(selected.account_id); await loadAccounts(0); } catch (caught) { setError(errorMessage(caught)); }
  };
  // The lifecycle instance is created once and owns the initial restore sequence.
  useEffect(() => { void refreshHealth(); void lifecycle.current!.restore().catch(() => { setSessionExpired(true); setError("Session expired. Please sign in again."); }); }, []);
  // The authenticated principal is reloaded only when the in-memory access token changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (accessToken) void loadCurrentAccount(); else { setCurrentAccount(null); setView("home"); } }, [accessToken]);
  // Metadata is refreshed after the principal changes; it must not re-fetch on local list state changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (isAdmin) void loadAdminMetadata(); }, [currentAccount?.account_id]);
  const displayRoles = roles.filter((role) => canManageRoles || role.code === "employee");
  const pageNumber = Math.floor(offset / 20) + 1;

  return <main className="app-shell"><section className="card">
    <p className="eyebrow">SM-R01-A · Development Foundation</p><h1>Chatalker</h1>
    {accessToken && currentAccount ? <>
      <header className="shell-header"><p>Authenticated main shell · {currentAccount.login}</p><button type="button" onClick={() => void signOut()}>Sign out</button></header>
      {isAdmin && <nav aria-label="Administrator navigation"><button type="button" onClick={() => void openAccounts()}>Employee management</button><button type="button" onClick={() => setView("home")}>Home</button></nav>}
      {view === "accounts" && <section aria-labelledby="account-list-title"><h2 id="account-list-title">Employee accounts</h2><div className="filters"><input aria-label="Search accounts" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search login" /><select aria-label="Account status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}><option value="">All statuses</option><option value="active">Active</option><option value="disabled">Disabled</option></select><select aria-label="Department" value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)}><option value="">All departments</option>{departments.map((department) => <option key={department.department_id} value={department.department_id}>{department.name}</option>)}</select><button type="button" onClick={() => void loadAccounts(0)}>Apply filters</button><button type="button" onClick={() => setView("create")}>Create employee</button></div>{loading ? <p>Loading accounts…</p> : accounts.length === 0 ? <p>No accounts match the current filters.</p> : <table><thead><tr><th>Login</th><th>Department</th><th>Role</th><th>Status</th><th /></tr></thead><tbody>{accounts.map((account) => <tr key={account.account_id}><td>{account.login}</td><td>{account.department?.name ?? "—"}</td><td>{account.role?.display_name ?? "—"}</td><td>{account.status}</td><td><button type="button" onClick={() => void openDetail(account.account_id)}>View</button></td></tr>)}</tbody></table>}<div className="pagination"><span>Page {pageNumber} · {total} accounts</span><button type="button" disabled={offset === 0 || loading} onClick={() => void loadAccounts(Math.max(0, offset - 20))}>Previous</button><button type="button" disabled={offset + 20 >= total || loading} onClick={() => void loadAccounts(offset + 20)}>Next</button></div></section>}
      {view === "create" && <section aria-labelledby="create-account-title"><h2 id="create-account-title">Create employee account</h2><input aria-label="New login" value={newLogin} onChange={(event) => setNewLogin(event.target.value)} placeholder="Login ID" /><input aria-label="Initial password" type="password" value={newInitialPassword} onChange={(event) => setNewInitialPassword(event.target.value)} placeholder="Initial password" /><select aria-label="New department" value={newDepartment} onChange={(event) => setNewDepartment(event.target.value)}><option value="">No department</option>{departments.map((department) => <option key={department.department_id} value={department.department_id}>{department.name}</option>)}</select><select aria-label="New role" value={newRole} onChange={(event) => setNewRole(event.target.value as Role["code"])}>{displayRoles.map((role) => <option key={role.code} value={role.code}>{role.display_name}</option>)}</select><button type="button" onClick={() => void submitCreate()}>Create account</button><button type="button" onClick={() => setView("accounts")}>Cancel</button></section>}
      {view === "detail" && selected && <section aria-labelledby="account-detail-title"><h2 id="account-detail-title">Account detail</h2><dl><dt>Login ID</dt><dd>{selected.login}</dd><dt>Account identifier</dt><dd>{selected.account_id}</dd><dt>Department</dt><dd>{selected.department?.name ?? "—"}</dd><dt>Role</dt><dd>{selected.role?.display_name ?? "—"}</dd><dt>Status</dt><dd>{selected.status}</dd></dl><label>Department <select value={selected.department?.department_id ?? ""} onChange={(event) => void saveSelected({ department_id: event.target.value })}>{departments.map((department) => <option key={department.department_id} value={department.department_id}>{department.name}</option>)}</select></label>{canManageRoles && selected.account_id !== currentAccount.account_id && <label>Role <select value={selected.role?.code ?? ""} onChange={(event) => void saveSelected({ role_code: event.target.value as Role["code"] })}>{roles.map((role) => <option key={role.code} value={role.code}>{role.display_name}</option>)}</select></label>}<button type="button" disabled={selected.status === "disabled"} onClick={() => void saveSelected({ status: "disabled" })}>Deactivate account</button><button type="button" onClick={() => setView("accounts")}>Back to accounts</button></section>}
      {view === "home" && <p>Use the administrator menu to manage employee accounts.</p>}
    </> : passwordChangeToken ? <><p>Change your password before continuing.</p><input aria-label="New password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="New password" /><button type="button" onClick={() => void completePasswordChange()}>Change password</button></> : <><p>{sessionExpired ? "Session expired. Sign in to continue." : "Sign in to Chatalker."}</p><input value={loginName} onChange={(event) => setLoginName(event.target.value)} placeholder="Login" /><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" /><button type="button" onClick={() => void signIn()}>Sign in</button></>}
    {error && <p role="alert">{error}</p>}<dl><dt>API base URL</dt><dd>{apiBaseUrl}</dd><dt>Backend health</dt><dd>{health.kind === "loading" && "Checking…"}{health.kind === "success" && `${health.data.status} (${health.data.database}; database is not checked)`}{health.kind === "error" && `Unavailable: ${health.message}`}</dd></dl><button type="button" onClick={() => void refreshHealth()}>Retry health check</button>
  </section></main>;
}
