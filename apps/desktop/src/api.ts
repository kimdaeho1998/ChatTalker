const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const apiBaseUrl = configuredApiBaseUrl || "http://127.0.0.1:8000";

export type HealthResponse = {
  status: "ok";
  service: string;
  database: "not_checked";
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

type Envelope<T> = { code: string; message: string; data: T };
export type Session = {
  access_token: string;
  refresh_token: string;
  session_id: string;
};

export class AuthApiError extends Error {
  constructor(readonly status: number, message = "Authentication failed") {
    super(message);
  }
}

async function authRequest<T>(path: string, init: RequestInit): Promise<Envelope<T>> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    throw new AuthApiError(response.status);
  }
  return response.json() as Promise<Envelope<T>>;
}

export async function login(login: string, password: string): Promise<Envelope<Session | { password_change_token: string }>> {
  return authRequest("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
}

export async function changePassword(
  current_password: string,
  new_password: string,
  password_change_token: string,
): Promise<Envelope<Session>> {
  return authRequest("/auth/password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password, new_password, password_change_token }),
  });
}

export async function refresh(refresh_token: string): Promise<Envelope<Session>> {
  return authRequest("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
}

export async function logout(accessToken: string): Promise<void> {
  await authRequest("/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
