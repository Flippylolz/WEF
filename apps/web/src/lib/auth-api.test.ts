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
