import createClient from "openapi-fetch";

import type { components, paths } from "@/generated/api";

export type RevealedContacts = components["schemas"]["RevealContactsResponse"];
export type RevealedContact = components["schemas"]["RevealedContactResponse"];

type Ready<T> = { state: "ready"; data: T };
type Failed = {
  state: "error";
  code?:
    | "unauthorized"
    | "forbidden"
    | "not_found"
    | "rate_limited"
    | "unavailable"
    | "unknown";
  message?: string;
};
export type RevealResult = Ready<RevealedContacts> | Failed;

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

function problemCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" ? code : undefined;
}

function problemMessage(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const detail = (error as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : undefined;
}

function mapStatus(status: number): Failed["code"] {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 429) return "rate_limited";
  if (status === 503) return "unavailable";
  return "unknown";
}

/** Reveal contacts for one offer. Call only after an explicit user gesture. */
export async function revealOfferContacts(
  offerId: string,
  options: RequestOptions = {},
): Promise<RevealResult> {
  try {
    const { data, error, response } = await client(options.fetcher).POST(
      "/api/v1/offers/{offer_id}/contacts/reveal",
      {
        params: { path: { offer_id: offerId } },
        // Mutations require JSON content-type even without a schema body.
        headers: { "Content-Type": "application/json" },
        body: {} as never,
        bodySerializer: () => "{}",
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return {
        state: "error",
        code: mapStatus(response.status),
        message: problemMessage(error) ?? problemCode(error),
      };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error", code: "unknown" };
  }
}
