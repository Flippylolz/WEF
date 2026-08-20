import createClient from "openapi-fetch";

import type { paths } from "@/generated/api";

export type FavoriteList =
  paths["/api/v1/favorites"]["get"]["responses"][200]["content"]["application/json"];
export type FavoriteLocation = FavoriteList["items"][number];

type Ready<T> = { state: "ready"; data: T };
type Failed = { state: "error" };
export type FavoriteResult<T> = Ready<T> | Failed;

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

export async function fetchFavorites(
  options: RequestOptions = {},
): Promise<FavoriteResult<FavoriteList>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/favorites",
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

export async function addFavorite(
  locationId: string,
  options: RequestOptions = {},
): Promise<FavoriteResult<null>> {
  try {
    const { response } = await client(options.fetcher).PUT(
      "/api/v1/favorites/{location_id}",
      {
        params: { path: { location_id: locationId } },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (response.status !== 204 && !response.ok) {
      return { state: "error" };
    }
    return { state: "ready", data: null };
  } catch {
    return { state: "error" };
  }
}

export async function removeFavorite(
  locationId: string,
  options: RequestOptions = {},
): Promise<FavoriteResult<null>> {
  try {
    const { response } = await client(options.fetcher).DELETE(
      "/api/v1/favorites/{location_id}",
      {
        params: { path: { location_id: locationId } },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (response.status !== 204 && !response.ok) {
      return { state: "error" };
    }
    return { state: "ready", data: null };
  } catch {
    return { state: "error" };
  }
}
