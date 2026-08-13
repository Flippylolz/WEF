import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_BBOX,
  fetchFacets,
  fetchLocationMap,
  fetchLocationOffers,
} from "@/lib/catalog-api";

const response = (body: object, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("catalog API", () => {
  it("requests the map with the bounded default viewport", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(new URL(request.url).searchParams.get("bbox")).toBe(DEFAULT_BBOX);
      return response({
        type: "FeatureCollection",
        features: [],
        meta: {
          request_id: "00000000-0000-4000-8000-000000000001",
          feature_count: 0,
          matching_offer_count: 0,
        },
      });
    });

    const result = await fetchLocationMap(fetcher);

    expect(result.state).toBe("ready");
  });

  it("loads facets and explicit selected-location history", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/filter-facets") {
        return response({
          districts: [],
          rooms: [],
          market_types: [],
          content_types: [],
          price_min_minor: null,
          price_max_minor: null,
          area_min_sqm: null,
          area_max_sqm: null,
          published_from: null,
          published_to: null,
        });
      }
      expect(url.pathname).toContain("10000000-0000-4000-8000-000000000001");
      expect(url.searchParams.get("include_non_matching")).toBe("true");
      return response({
        items: [],
        matching_count: 0,
        total_count: 0,
        next_cursor: null,
      });
    });

    expect((await fetchFacets(fetcher)).state).toBe("ready");
    expect(
      (
        await fetchLocationOffers(
          "10000000-0000-4000-8000-000000000001",
          fetcher,
        )
      ).state,
    ).toBe("ready");
  });

  it("returns a stable error state for transport and API failures", async () => {
    const rejected = vi.fn(async () => {
      throw new Error("offline");
    });
    const failed = vi.fn(async () => response({}, 503));

    expect((await fetchLocationMap(rejected)).state).toBe("error");
    expect((await fetchFacets(failed)).state).toBe("error");
  });
});
