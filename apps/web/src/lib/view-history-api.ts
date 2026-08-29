import createClient from "openapi-fetch";

import type { paths } from "@/generated/api";

export type AccountVisit =
  paths["/api/v1/view-history/visits/{visit_id}"]["put"]["responses"][200]["content"]["application/json"];
export type ViewedOffer =
  paths["/api/v1/view-history/offers/{offer_id}"]["put"]["responses"][200]["content"]["application/json"];
export type ViewedOfferList =
  paths["/api/v1/view-history/offers"]["get"]["responses"][200]["content"]["application/json"];

type Ready<T> = { state: "ready"; data: T };
type Failed = { state: "error" };
export type ViewHistoryResult<T> = Ready<T> | Failed;

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

export async function startAccountVisit(
  visitId: string,
  options: RequestOptions = {},
): Promise<ViewHistoryResult<AccountVisit>> {
  try {
    const { data, error, response } = await client(options.fetcher).PUT(
      "/api/v1/view-history/visits/{visit_id}",
      {
        params: { path: { visit_id: visitId } },
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function markOfferViewed(
  offerId: string,
  options: RequestOptions = {},
): Promise<ViewHistoryResult<ViewedOffer>> {
  try {
    const { data, error, response } = await client(options.fetcher).PUT(
      "/api/v1/view-history/offers/{offer_id}",
      {
        params: { path: { offer_id: offerId } },
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function fetchViewedOffers(
  options: RequestOptions = {},
): Promise<ViewHistoryResult<ViewedOfferList>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/view-history/offers",
      {
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}
