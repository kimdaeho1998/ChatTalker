import { apiBaseUrl, AuthApiError } from "./api";

export type AuthorizedFetch = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

type Envelope<T> = { code: string; message: string; data: T };

export type Department = { department_id: string; code: string; name: string };
export type Role = { code: "chief_admin" | "standard_admin" | "employee"; display_name: string };
export type Account = {
  account_id: string;
  login: string;
  status: "active" | "disabled";
  role: Role | null;
  department: Department | null;
  password_change_required: boolean;
};
export type CurrentAccount = Account & { role_code: Role["code"]; admin_scopes: Department[] };
export type AccountPage = { items: Account[]; total: number; limit: number; offset: number };

export type AccountFilters = {
  limit?: number;
  offset?: number;
  search?: string;
  status?: "active" | "disabled";
  department_id?: string;
};

async function request<T>(authorizedFetch: AuthorizedFetch, path: string, init: RequestInit = {}): Promise<T> {
  const response = await authorizedFetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) throw new AuthApiError(response.status);
  return ((await response.json()) as Envelope<T>).data;
}

export function getCurrentAccount(authorizedFetch: AuthorizedFetch): Promise<CurrentAccount> {
  return request(authorizedFetch, "/auth/me");
}

export function getAccounts(authorizedFetch: AuthorizedFetch, filters: AccountFilters = {}): Promise<AccountPage> {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return request(authorizedFetch, `/admin/accounts${query.size ? `?${query}` : ""}`);
}

export function getAccount(authorizedFetch: AuthorizedFetch, accountId: string): Promise<Account> {
  return request(authorizedFetch, `/admin/accounts/${encodeURIComponent(accountId)}`);
}

export function getDepartments(authorizedFetch: AuthorizedFetch): Promise<Department[]> {
  return request<{ items: Department[] }>(authorizedFetch, "/admin/departments").then((data) => data.items);
}

export function getRoles(authorizedFetch: AuthorizedFetch): Promise<Role[]> {
  return request<{ items: Role[] }>(authorizedFetch, "/admin/roles").then((data) => data.items);
}

export function createAccount(
  authorizedFetch: AuthorizedFetch,
  payload: { login: string; initial_password: string; department_id?: string; role_code: Role["code"] },
): Promise<{ account_id: string }> {
  return request(authorizedFetch, "/admin/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateAccount(
  authorizedFetch: AuthorizedFetch,
  accountId: string,
  payload: { status?: "active" | "disabled"; role_code?: Role["code"]; department_id?: string },
): Promise<{ account_id: string }> {
  return request(authorizedFetch, `/admin/accounts/${encodeURIComponent(accountId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
