import { describe, expect, it, vi } from "vitest";

import {
  changePassword,
  fetchCurrentAccount,
  loginAccount,
  logoutAccount,
  registerAccount,
  revokeAllSessions,
} from "@/lib/auth-api";

const account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user" as const,
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("auth-api", () => {
  it("returns null for unauthenticated me requests", async () => {
    const fetcher = vi.fn(async () => jsonResponse(401, { detail: "nope" }));
    const result = await fetchCurrentAccount({ fetcher });
    expect(result).toEqual({ state: "ready", data: null });
  });

  it("registers and logs in with credentials included", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.credentials).toBe("include");
      if (request.url.endsWith("/api/v1/auth/register")) {
        return jsonResponse(201, account);
      }
      if (request.url.endsWith("/api/v1/auth/login")) {
        return jsonResponse(200, account);
      }
      throw new Error(`unexpected ${request.url}`);
    });

    const registered = await registerAccount(
      { username: "warsaw", password: "longenough123" },
      { fetcher },
    );
    const loggedIn = await loginAccount(
      { username: "warsaw", password: "longenough123" },
      { fetcher },
    );

    expect(registered).toEqual({ state: "ready", data: account });
    expect(loggedIn).toEqual({ state: "ready", data: account });
  });

  it("surfaces logout failures", async () => {
    const fetcher = vi.fn(async () =>
      jsonResponse(503, { detail: "Unavailable." }),
    );
    const result = await logoutAccount({ fetcher });
    expect(result).toEqual({ state: "error", message: "Unavailable." });
  });

  it("returns the current account and maps problem details", async () => {
    const ok = vi.fn(async () => jsonResponse(200, account));
    const failed = vi.fn(async () => jsonResponse(500, { detail: "nope" }));
    const unreadable = vi.fn(async () => jsonResponse(500, { detail: 12 }));
    const offline = vi.fn(async () => {
      throw new Error("offline");
    });

    expect(await fetchCurrentAccount({ fetcher: ok })).toEqual({
      state: "ready",
      data: account,
    });
    expect(await fetchCurrentAccount({ fetcher: failed })).toEqual({
      state: "error",
      message: "nope",
    });
    expect(await fetchCurrentAccount({ fetcher: unreadable })).toEqual({
      state: "error",
    });
    expect(await fetchCurrentAccount({ fetcher: offline })).toEqual({
      state: "error",
    });
  });

  it("surfaces register, login, and password mutation failures", async () => {
    const failed = vi.fn(async () => jsonResponse(400, { detail: "taken" }));
    const offline = vi.fn(async () => {
      throw new Error("offline");
    });

    expect(
      await registerAccount(
        { username: "warsaw", password: "longenough123" },
        { fetcher: failed },
      ),
    ).toEqual({ state: "error", message: "taken" });
    expect(
      await loginAccount(
        { username: "warsaw", password: "longenough123" },
        { fetcher: failed },
      ),
    ).toEqual({ state: "error", message: "taken" });
    expect(await logoutAccount({ fetcher: offline })).toEqual({
      state: "error",
    });
    expect(
      await changePassword(
        {
          current_password: "longenough123",
          new_password: "newlongenough456",
        },
        { fetcher: failed },
      ),
    ).toEqual({ state: "error", message: "taken" });
    expect(await revokeAllSessions({ fetcher: offline })).toEqual({
      state: "error",
    });
    expect(
      await registerAccount(
        { username: "warsaw", password: "longenough123" },
        { fetcher: offline },
      ),
    ).toEqual({ state: "error" });
    expect(
      await loginAccount(
        { username: "warsaw", password: "longenough123" },
        { fetcher: offline },
      ),
    ).toEqual({ state: "error" });
    expect(
      await changePassword(
        {
          current_password: "longenough123",
          new_password: "newlongenough456",
        },
        { fetcher: offline },
      ),
    ).toEqual({ state: "error" });
  });

  it("logs out and revokes sessions on success and HTTP errors", async () => {
    const ok = vi.fn(async () => new Response(null, { status: 204 }));
    expect(await logoutAccount({ fetcher: ok })).toEqual({
      state: "ready",
      data: null,
    });

    const failed = vi.fn(async () => jsonResponse(400, { detail: "blocked" }));
    expect(await revokeAllSessions({ fetcher: failed })).toEqual({
      state: "error",
      message: "blocked",
    });
    expect(await logoutAccount({ fetcher: failed })).toEqual({
      state: "error",
      message: "blocked",
    });

    const unreadable = vi.fn(async () => jsonResponse(400, { detail: 12 }));
    expect(await revokeAllSessions({ fetcher: unreadable })).toEqual({
      state: "error",
    });

    const controller = new AbortController();
    const signaled = vi.fn(async (request: Request) => {
      expect(request.signal).toBe(controller.signal);
      return new Response(null, { status: 204 });
    });
    await logoutAccount({ fetcher: signaled, signal: controller.signal });
    await revokeAllSessions({ fetcher: signaled, signal: controller.signal });
  });

  it("changes password and revokes all sessions", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.credentials).toBe("include");
      expect(request.headers.get("Content-Type")).toBe("application/json");
      if (request.url.endsWith("/api/v1/auth/password")) {
        return new Response(null, { status: 204 });
      }
      if (request.url.endsWith("/api/v1/auth/sessions/revoke-all")) {
        return new Response(null, { status: 204 });
      }
      throw new Error(`unexpected ${request.url}`);
    });

    await expect(
      changePassword(
        {
          current_password: "longenough123",
          new_password: "newlongenough456",
        },
        { fetcher },
      ),
    ).resolves.toEqual({ state: "ready", data: null });
    await expect(revokeAllSessions({ fetcher })).resolves.toEqual({
      state: "ready",
      data: null,
    });
  });
});
