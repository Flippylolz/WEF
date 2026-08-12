import createClient from "openapi-fetch";

import type { paths } from "@/generated/api";

export type FilterFacets =
  paths["/api/v1/filter-facets"]["get"]["responses"][200]["content"]["application/json"];
export type LocationMap =
  paths["/api/v1/map/locations"]["get"]["responses"][200]["content"]["application/json"];
export type LocationMapFeature = LocationMap["features"][number];
export type LocationOfferPage =
  paths["/api/v1/locations/{location_id}/offers"]["get"]["responses"][200]["content"]["application/json"];

export const DEFAULT_BBOX = "20.7,52.0,21.4,52.4";

type Ready<T> = { state: "ready"; data: T };
type Failed = { state: "error" };
export type ApiResult<T> = Ready<T> | Failed;
type Fetcher = (request: Request) => Promise<Response>;

function apiBaseUrl() {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return process.env.WEF_API_URL?.trim() || "http://127.0.0.1:8000";
}

function client(fetcher?: Fetcher) {
  return createClient<paths>({
    baseUrl: apiBaseUrl(),
    ...(fetcher ? { fetch: fetcher } : {}),
  });
}

export async function fetchLocationMap(
  fetcher?: Fetcher,
): Promise<ApiResult<LocationMap>> {
  try {
    const { data, error, response } = await client(fetcher).GET(
      "/api/v1/map/locations",
      {
        params: { query: { bbox: DEFAULT_BBOX } },
        cache: "no-store",
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    const features: LocationMap["features"] = data.features.map((feature) => {
      const [longitude, latitude] = feature.geometry.coordinates;
      if (longitude === undefined || latitude === undefined) {
        throw new Error("Invalid point coordinates");
      }
      const coordinates: [number, number] = [longitude, latitude];
      return {
        ...feature,
        geometry: { ...feature.geometry, coordinates },
      };
    });
    return { state: "ready", data: { ...data, features } };
  } catch {
    return { state: "error" };
  }
}

export async function fetchFacets(
  fetcher?: Fetcher,
): Promise<ApiResult<FilterFacets>> {
  try {
    const { data, error, response } = await client(fetcher).GET(
      "/api/v1/filter-facets",
      { cache: "no-store" },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function fetchLocationOffers(
  locationId: string,
  fetcher?: Fetcher,
): Promise<ApiResult<LocationOfferPage>> {
  try {
    const { data, error, response } = await client(fetcher).GET(
      "/api/v1/locations/{location_id}/offers",
      {
        params: {
          path: { location_id: locationId },
          query: {
            bbox: DEFAULT_BBOX,
            include_non_matching: true,
            limit: 20,
          },
        },
        cache: "no-store",
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
