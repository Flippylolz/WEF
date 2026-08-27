import createClient from "openapi-fetch";

import type { operations, paths } from "@/generated/api";
import { DEFAULT_BBOX, type MapLocationQuery } from "@/lib/map-search-params";

export { DEFAULT_BBOX } from "@/lib/map-search-params";
export type { MapLocationQuery } from "@/lib/map-search-params";

export type FilterFacets =
  paths["/api/v1/filter-facets"]["get"]["responses"][200]["content"]["application/json"];
export type QuickFilterList =
  paths["/api/v1/quick-filters"]["get"]["responses"][200]["content"]["application/json"];
export type QuickFilterPreset = QuickFilterList["items"][number];
export type LocationMap =
  paths["/api/v1/map/locations"]["get"]["responses"][200]["content"]["application/json"];
export type LocationMapFeature = LocationMap["features"][number];
export type LocationOfferPage =
  paths["/api/v1/locations/{location_id}/offers"]["get"]["responses"][200]["content"]["application/json"];
export type OfferDetail =
  paths["/api/v1/offers/{offer_id}"]["get"]["responses"][200]["content"]["application/json"];
export type ViewportListingPage =
  paths["/api/v1/listings"]["get"]["responses"][200]["content"]["application/json"];
export type ViewportListing = ViewportListingPage["items"][number];

type Ready<T> = { state: "ready"; data: T };
type Failed = { state: "error" };
type NotFound = { state: "not_found" };
export type ApiResult<T> = Ready<T> | Failed;
export type OfferDetailResult = Ready<OfferDetail> | NotFound | Failed;
type Fetcher = (request: Request) => Promise<Response>;
type RequestOptions = {
  fetcher?: Fetcher;
  signal?: AbortSignal;
};
type LocationOffersQuery =
  operations["listLocationOffers"]["parameters"]["query"];

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
  query: MapLocationQuery = { bbox: DEFAULT_BBOX },
  options: RequestOptions = {},
): Promise<ApiResult<LocationMap>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/map/locations",
      {
        params: { query },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
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

export async function fetchQuickFilters(
  options: RequestOptions = {},
): Promise<ApiResult<QuickFilterList>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/quick-filters",
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

export async function fetchFacets(
  options: RequestOptions = {},
): Promise<ApiResult<FilterFacets>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/filter-facets",
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

export async function fetchLocationOffers(
  locationId: string,
  query: MapLocationQuery = { bbox: DEFAULT_BBOX },
  options: RequestOptions = {},
): Promise<ApiResult<LocationOfferPage>> {
  try {
    const offersQuery: LocationOffersQuery = {
      ...query,
      include_non_matching: true,
      limit: 20,
    };
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/locations/{location_id}/offers",
      {
        params: {
          path: { location_id: locationId },
          query: offersQuery,
        },
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

export async function fetchOfferDetail(
  offerId: string,
  options: RequestOptions = {},
): Promise<OfferDetailResult> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/offers/{offer_id}",
      {
        params: { path: { offer_id: offerId } },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (response.status === 404) {
      return { state: "not_found" };
    }
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    return { state: "ready", data };
  } catch {
    return { state: "error" };
  }
}

export async function fetchViewportListings(
  query: MapLocationQuery & { cursor?: string; limit?: number } = {
    bbox: DEFAULT_BBOX,
  },
  options: RequestOptions = {},
): Promise<ApiResult<ViewportListingPage>> {
  try {
    const { data, error, response } = await client(options.fetcher).GET(
      "/api/v1/listings",
      {
        params: { query },
        cache: "no-store",
        ...(options.signal ? { signal: options.signal } : {}),
      },
    );
    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }
    const items: ViewportListingPage["items"] = data.items.map((item) => {
      const [longitude, latitude] = item.location.geometry.coordinates;
      if (longitude === undefined || latitude === undefined) {
        throw new Error("Invalid point coordinates");
      }
      const coordinates: [number, number] = [longitude, latitude];
      return {
        ...item,
        location: {
          ...item.location,
          geometry: { ...item.location.geometry, coordinates },
        },
      };
    });
    return { state: "ready", data: { ...data, items } };
  } catch {
    return { state: "error" };
  }
}
