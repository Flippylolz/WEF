import createClient from "openapi-fetch";

import type { paths } from "@/generated/api";

export type Account =
  paths["/api/v1/auth/me"]["get"]["responses"][200]["content"]["application/json"];

type Ready<T> = { state: "ready"; data: T };
type Failed = { state: "error"; message?: string };
export type AuthResult<T> = Ready<T> | Failed;

type Fetcher = (request: Request) => Promise<Response>;
type RequestOptions = {
  fetcher?: Fetcher;
  signal?: AbortSignal;
};

function apiBaseUrl() {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return process.env.WEF_API_URL?.trim() || "http://127.0.0.1:8000";
}

function client(fetcher?: Fetcher) {
  return createClient<paths>({
    baseUrl: apiBaseUrl(),
    credentials: "include",
    ...(fetcher ? { fetch: fetcher } : {}),
  });
}

function problemMessage(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const detail = (error as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : undefined;
}

export async function fetchCurrentAccount(
  options: RequestOptions = {},
): Promise<AuthResult<Account | null>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/auth/me",
      {
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (response.status === 401) {
      return { state: "ready", data: null };
    }
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error", message: problemMessage(error) };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function registerAccount(
  payload: { username: string; password: string },
  options: RequestOptions = {},
): Promise<AuthResult<Account>> {
  try {
    const { data, error, response } = await client(options.fetcher).POST(
      "/api/v1/auth/register",
      {
        body: payload,
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error", message: problemMessage(error) };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function loginAccount(
  payload: { username: string; password: string },
  options: RequestOptions = {},
): Promise<AuthResult<Account>> {
  try {
    const { data, error, response } = await client(options.fetcher).POST(
      "/api/v1/auth/login",
      {
        body: payload,
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error", message: problemMessage(error) };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function logoutAccount(
  options: RequestOptions = {},
): Promise<AuthResult<null>> {
  try {
    const { error, response } = await client(options.fetcher).POST(
      "/api/v1/auth/logout",
      {
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined) {
      return { state: "error", message: problemMessage(error) };
    }
    return { state: "ready", data: null };
  } catch {
    return { state: "error" };
  }
}
