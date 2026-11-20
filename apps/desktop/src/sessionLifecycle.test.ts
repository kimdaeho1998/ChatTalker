import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthApiError, type Session } from "./api";
import { SessionLifecycle, type SecureTokenStorage } from "./sessionLifecycle";

const initialSession: Session = { access_token: "access-1", refresh_token: "refresh-1", session_id: "session-1" };
const rotatedSession: Session = { access_token: "access-2", refresh_token: "refresh-2", session_id: "session-2" };

function storageWith(token: string | null = null): SecureTokenStorage & { token: string | null } {
  return {
    token,
    async store(value) { this.token = value; },
    async load() { return this.token; },
    async remove() { this.token = null; },
  };
}

function createLifecycle(storage = storageWith(), api = { refresh: vi.fn(async () => rotatedSession), logout: vi.fn(async () => undefined) }) {
  const access = vi.fn();
  return { lifecycle: new SessionLifecycle(storage, api, access), storage, api, access };
}

afterEach(() => vi.unstubAllGlobals());

describe("SessionLifecycle", () => {
  it("shares one refresh request across concurrent 401 responses and retries once", async () => {
    const { lifecycle, api } = createLifecycle();
    const generation = lifecycle.beginAuthentication();
    await lifecycle.establish(initialSession, generation);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const responses = await Promise.all([lifecycle.authorizedFetch("/protected"), lifecycle.authorizedFetch("/protected")]);
    expect(responses.map((response) => response.status)).toEqual([200, 200]);
    expect(api.refresh).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("does not retry indefinitely after a refreshed request is still unauthorized", async () => {
    const { lifecycle, api } = createLifecycle();
    const generation = lifecycle.beginAuthentication();
    await lifecycle.establish(initialSession, generation);
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await lifecycle.authorizedFetch("/protected");
    expect(response.status).toBe(401);
    expect(api.refresh).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("restores a session by rotating the persisted refresh token", async () => {
    const storage = storageWith(initialSession.refresh_token);
    const { lifecycle, access } = createLifecycle(storage);

    await expect(lifecycle.restore()).resolves.toEqual(rotatedSession);
    expect(storage.token).toBe(rotatedSession.refresh_token);
    expect(access).toHaveBeenLastCalledWith(rotatedSession.access_token);
  });

  it("fences a late refresh result after a new login generation begins", async () => {
    let resolveRefresh!: (session: Session) => void;
    const api = { refresh: vi.fn(() => new Promise<Session>((resolve) => { resolveRefresh = resolve; })), logout: vi.fn(async () => undefined) };
    const { lifecycle, storage, access } = createLifecycle(storageWith(initialSession.refresh_token), api);
    const restoring = lifecycle.restore();
    await vi.waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(1));
    const newGeneration = lifecycle.beginAuthentication();
    const newSession = { access_token: "access-new", refresh_token: "refresh-new", session_id: "session-new" };
    await lifecycle.establish(newSession, newGeneration);
    resolveRefresh(rotatedSession);

    await expect(restoring).resolves.toBeNull();
    expect(storage.token).toBe("refresh-new");
    expect(access).toHaveBeenLastCalledWith(newSession.access_token);
  });

  it("prevents a delayed credential write from restoring a logged-out session", async () => {
    let releaseStore!: () => void;
    const storage = storageWith();
    storage.store = vi.fn(() => new Promise<void>((resolve) => { releaseStore = resolve; }));
    const { lifecycle, access } = createLifecycle(storage);
    const generation = lifecycle.beginAuthentication();
    const establishing = lifecycle.establish(initialSession, generation);
    await vi.waitFor(() => expect(storage.store).toHaveBeenCalledTimes(1));
    const loggingOut = lifecycle.logout();
    releaseStore();

    await Promise.all([establishing, loggingOut]);
    expect(storage.token).toBeNull();
    expect(access).toHaveBeenLastCalledWith(null);
  });

  it("clears local credentials after a definitive refresh rejection but not a network failure", async () => {
    const rejected = createLifecycle(storageWith(initialSession.refresh_token), {
      refresh: vi.fn(async () => { throw new AuthApiError(401); }),
      logout: vi.fn(async () => undefined),
    });
    await expect(rejected.lifecycle.restore()).rejects.toBeInstanceOf(AuthApiError);
    expect(rejected.storage.token).toBeNull();

    const unavailable = createLifecycle(storageWith(initialSession.refresh_token), {
      refresh: vi.fn(async () => { throw new TypeError("network unavailable"); }),
      logout: vi.fn(async () => undefined),
    });
    await expect(unavailable.lifecycle.restore()).rejects.toBeInstanceOf(TypeError);
    expect(unavailable.storage.token).toBe(initialSession.refresh_token);
  });

  it("revokes the server session before clearing the local credential", async () => {
    const { lifecycle, storage, api, access } = createLifecycle();
    const generation = lifecycle.beginAuthentication();
    await lifecycle.establish(initialSession, generation);

    await expect(lifecycle.logout()).resolves.toBe("server_revoked");
    expect(api.logout).toHaveBeenCalledWith(initialSession.access_token);
    expect(storage.token).toBeNull();
    expect(access).toHaveBeenLastCalledWith(null);
  });

  it("does not refresh when logout wins a session restore race", async () => {
    let releaseLoad!: (token: string | null) => void;
    const storage = storageWith();
    storage.load = vi.fn(() => new Promise<string | null>((resolve) => { releaseLoad = resolve; }));
    const { lifecycle, api } = createLifecycle(storage);
    const restoring = lifecycle.restore();
    await vi.waitFor(() => expect(storage.load).toHaveBeenCalledTimes(1));
    const loggingOut = lifecycle.logout();
    releaseLoad(initialSession.refresh_token);

    await Promise.all([restoring, loggingOut]);
    expect(api.refresh).not.toHaveBeenCalled();
    expect(storage.token).toBeNull();
  });
});
