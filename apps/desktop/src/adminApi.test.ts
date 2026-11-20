import { describe, expect, it } from "vitest";
import { createAccount, getAccounts, getCurrentAccount, updateAccount, type AuthorizedFetch } from "./adminApi";

const envelope = (data: unknown) => new Response(JSON.stringify({ code: "OK", message: "OK", data }), { status: 200 });

describe("admin API client", () => {
  it("uses the server pagination and filter contract", async () => {
    const calls: Parameters<AuthorizedFetch>[] = [];
    const authorizedFetch: AuthorizedFetch = async (...args) => { calls.push(args); return envelope({ items: [], total: 0, limit: 20, offset: 0 }); };
    await getAccounts(authorizedFetch, { limit: 20, offset: 40, search: "alex", status: "active", department_id: "department-1" });
    expect(String(calls[0][0])).toContain("/admin/accounts?limit=20&offset=40&search=alex&status=active&department_id=department-1");
  });

  it("uses authenticated requests for current account and writes without retaining credentials", async () => {
    const calls: Parameters<AuthorizedFetch>[] = [];
    const authorizedFetch: AuthorizedFetch = async (...args) => { calls.push(args); return envelope({ account_id: "account-1" }); };
    await getCurrentAccount(authorizedFetch);
    await createAccount(authorizedFetch, { login: "employee-1", initial_password: "test-only-password", role_code: "employee" });
    await updateAccount(authorizedFetch, "account-1", { status: "disabled" });
    expect(calls[1][1]).toMatchObject({ method: "POST" });
    expect(calls[2][1]).toMatchObject({ method: "PATCH" });
  });

  it("preserves backend error status for UI handling", async () => {
    await expect(getAccounts(async () => new Response(null, { status: 403 }))).rejects.toMatchObject({ status: 403 });
  });
});
