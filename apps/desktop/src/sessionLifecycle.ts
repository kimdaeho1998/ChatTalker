import { AuthApiError, type Session } from "./api";

export type SecureTokenStorage = {
  store(token: string): Promise<void>;
  load(): Promise<string | null>;
  remove(): Promise<void>;
};

export type SessionApi = {
  refresh(token: string): Promise<Session>;
  logout(accessToken: string): Promise<void>;
};

export type LogoutResult = "server_revoked" | "server_unavailable";

export class SessionLifecycle {
  private accessToken: string | null = null;
  private sessionGeneration = 0;
  private refreshFlight: Promise<Session | null> | null = null;
  private credentialQueue: Promise<void> = Promise.resolve();

  constructor(
    private readonly storage: SecureTokenStorage,
    private readonly api: SessionApi,
    private readonly onAccessToken: (token: string | null) => void,
  ) {}

  beginAuthentication(): number {
    this.sessionGeneration += 1;
    this.setAccessToken(null);
    return this.sessionGeneration;
  }

  async establish(session: Session, generation: number): Promise<boolean> {
    if (generation !== this.sessionGeneration) return false;
    this.setAccessToken(session.access_token);
    try {
      await this.enqueueCredentialOperation(async () => {
        if (generation !== this.sessionGeneration) return;
        await this.storage.store(session.refresh_token);
      });
    } catch (error) {
      if (generation === this.sessionGeneration) this.setAccessToken(null);
      throw error;
    }
    return generation === this.sessionGeneration;
  }

  async restore(): Promise<Session | null> {
    const generation = this.sessionGeneration;
    const token = await this.enqueueCredentialOperation(() => this.storage.load());
    if (!token || generation !== this.sessionGeneration) return null;
    try {
      return await this.refreshSingleFlight(token, generation);
    } catch (error) {
      if (generation === this.sessionGeneration && error instanceof AuthApiError && error.status === 401) {
        await this.clearLocalSession(generation);
      }
      throw error;
    }
  }

  async authorizedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
    const generation = this.sessionGeneration;
    const first = await fetch(input, this.withAuthorization(init));
    if (first.status !== 401 || generation !== this.sessionGeneration) return first;

    const renewed = await this.refreshSingleFlight(undefined, generation);
    if (!renewed || generation !== this.sessionGeneration) return first;
    return fetch(input, this.withAuthorization(init));
  }

  async logout(): Promise<LogoutResult> {
    const accessToken = this.accessToken;
    this.sessionGeneration += 1;
    this.setAccessToken(null);

    let result: LogoutResult = "server_revoked";
    if (accessToken) {
      try {
        await this.api.logout(accessToken);
      } catch {
        result = "server_unavailable";
      }
    }
    await this.enqueueCredentialOperation(() => this.storage.remove());
    return result;
  }

  private async refreshSingleFlight(token: string | undefined, generation: number): Promise<Session | null> {
    if (this.refreshFlight) return this.refreshFlight;

    const flight = (async () => {
      const refreshToken = token ?? (await this.enqueueCredentialOperation(() => this.storage.load()));
      if (!refreshToken || generation !== this.sessionGeneration) return null;

      let session: Session;
      try {
        session = await this.api.refresh(refreshToken);
      } catch (error) {
        if (generation === this.sessionGeneration && error instanceof AuthApiError && error.status === 401) {
          await this.clearLocalSession(generation);
        }
        throw error;
      }
      if (generation !== this.sessionGeneration) return null;
      return (await this.establish(session, generation)) ? session : null;
    })();
    this.refreshFlight = flight;
    try {
      return await flight;
    } finally {
      if (this.refreshFlight === flight) this.refreshFlight = null;
    }
  }

  private async clearLocalSession(generation: number): Promise<void> {
    if (generation !== this.sessionGeneration) return;
    this.sessionGeneration += 1;
    this.setAccessToken(null);
    await this.enqueueCredentialOperation(() => this.storage.remove());
  }

  private enqueueCredentialOperation<T>(operation: () => Promise<T>): Promise<T> {
    const next = this.credentialQueue.catch(() => undefined).then(operation);
    this.credentialQueue = next.then(
      () => undefined,
      () => undefined,
    );
    return next;
  }

  private withAuthorization(init: RequestInit): RequestInit {
    const headers = new Headers(init.headers);
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    return { ...init, headers };
  }

  private setAccessToken(token: string | null): void {
    this.accessToken = token;
    this.onAccessToken(token);
  }
}
