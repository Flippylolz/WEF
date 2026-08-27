import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_BBOX,
  fetchFacets,
  fetchLocationMap,
  fetchLocationOffers,
  fetchOfferDetail,
  fetchQuickFilters,
  fetchViewportListings,
} from "@/lib/catalog-api";

const response = (body: object, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("catalog API", () => {
  it("loads paginated viewport listings with cursor and limit", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      expect(url.pathname).toBe("/api/v1/listings");
      expect(url.searchParams.get("bbox")).toBe(DEFAULT_BBOX);
      expect(url.searchParams.get("cursor")).toBe("next");
      expect(url.searchParams.get("limit")).toBe("20");
      return response({
        items: [
          {
            id: "20000000-0000-4000-8000-000000000001",
            content_type: "development",
            market_type: "primary",
            display_name: "development · primary",
            data_confidence: "complete",
            published_at: "2026-08-01T10:00:00Z",
            currency: "PLN",
            price_min_minor: 80_000_000,
            price_max_minor: 125_000_000,
            parking_price_min_minor: null,
            parking_price_max_minor: null,
            parking_included_in_price: false,
            storage_price_min_minor: null,
            storage_price_max_minor: null,
            storage_included_in_price: false,
            area_min_sqm: "35.00",
            area_max_sqm: "71.50",
            rooms_min: 1,
            rooms_max: 3,
            floor_label: null,
            delivery_label: null,
            location: {
              id: "10000000-0000-4000-8000-000000000001",
              display_name: "Synthetic Central Residence",
              display_address: "Synthetic address 1, Warsaw",
              district: "srodmiescie",
              coordinate_precision: "address",
              confidence: "high",
              geometry: {
                type: "Point",
                coordinates: [21.0122, 52.2297],
              },
            },
          },
        ],
        matching_count: 1,
        next_cursor: null,
      });
    });

    const result = await fetchViewportListings(
      { bbox: DEFAULT_BBOX, cursor: "next", limit: 20 },
      { fetcher },
    );

    expect(result.state).toBe("ready");
    if (result.state === "ready") {
      expect(result.data.items[0]?.location.display_name).toBe(
        "Synthetic Central Residence",
      );
      expect(result.data.items[0]?.location.geometry.coordinates).toEqual([
        21.0122, 52.2297,
      ]);
    }
  });

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

    const result = await fetchLocationMap({ bbox: DEFAULT_BBOX }, { fetcher });

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

    expect((await fetchFacets({ fetcher })).state).toBe("ready");
    expect(
      (
        await fetchLocationOffers(
          "10000000-0000-4000-8000-000000000001",
          { bbox: DEFAULT_BBOX },
          { fetcher },
        )
      ).state,
    ).toBe("ready");
  });

  it("passes every filter and AbortSignal through the typed client", async () => {
    const controller = new AbortController();
    const fetcher = vi.fn(async (request: Request) => {
      const params = new URL(request.url).searchParams;
      expect(params.get("price_min")).toBe("80000000");
      expect(params.get("price_max")).toBe("125000000");
      expect(params.get("area_min")).toBe("35");
      expect(params.get("area_max")).toBe("71.5");
      expect(params.getAll("rooms")).toEqual(["1", "3"]);
      expect(params.getAll("district")).toEqual(["ochota", "wola"]);
      expect(params.getAll("market_type")).toEqual(["secondary"]);
      expect(params.getAll("content_type")).toEqual(["unit"]);
      expect(params.get("published_from")).toBe("2026-08-01T00:00:00.000Z");
      expect(params.get("published_to")).toBe("2026-08-31T23:59:59.999Z");
      expect(request.signal.aborted).toBe(false);
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

    const result = await fetchLocationMap(
      {
        bbox: "20.8,52.1,21.2,52.3",
        price_min: 80_000_000,
        price_max: 125_000_000,
        area_min: "35",
        area_max: "71.5",
        rooms: [1, 3],
        district: ["ochota", "wola"],
        market_type: ["secondary"],
        content_type: ["unit"],
        published_from: "2026-08-01T00:00:00.000Z",
        published_to: "2026-08-31T23:59:59.999Z",
      },
      { fetcher, signal: controller.signal },
    );

    expect(result.state).toBe("ready");
  });

  it("returns a stable error state for transport and API failures", async () => {
    const rejected = vi.fn(async () => {
      throw new Error("offline");
    });
    const failed = vi.fn(async () => response({}, 503));

    expect(
      (await fetchLocationMap({ bbox: DEFAULT_BBOX }, { fetcher: rejected }))
        .state,
    ).toBe("error");
    expect((await fetchFacets({ fetcher: failed })).state).toBe("error");
    expect((await fetchQuickFilters({ fetcher: failed })).state).toBe("error");
    expect(
      (
        await fetchLocationOffers(
          "loc",
          { bbox: DEFAULT_BBOX },
          { fetcher: failed },
        )
      ).state,
    ).toBe("error");
    expect((await fetchOfferDetail("offer", { fetcher: failed })).state).toBe(
      "error",
    );
    expect((await fetchOfferDetail("offer", { fetcher: rejected })).state).toBe(
      "error",
    );
  });

  it("loads quick filters and offer detail including not-found", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      const url = new URL(request.url);
      if (url.pathname === "/api/v1/quick-filters") {
        return response({
          items: [{ id: "last_day", label_key: "quickFilter.last_day" }],
        });
      }
      if (url.pathname.endsWith("/offers/missing")) {
        return response({ detail: "gone" }, 404);
      }
      if (url.pathname.endsWith("/offers/ready")) {
        return response({
          id: "ready",
          content_type: "unit",
          market_type: "secondary",
          display_name: "unit · secondary",
          data_confidence: "complete",
          published_at: "2026-08-01T10:00:00Z",
          currency: "PLN",
          price_min_minor: null,
          price_max_minor: null,
          parking_price_min_minor: null,
          parking_price_max_minor: null,
          parking_included_in_price: false,
          storage_price_min_minor: null,
          storage_price_max_minor: null,
          storage_included_in_price: false,
          area_min_sqm: null,
          area_max_sqm: null,
          rooms_min: null,
          rooms_max: null,
          floor_label: null,
          delivery_label: null,
          public_source_text: "Masked.",
          parser_version: "synthetic-m1-v1",
          location: {
            id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address",
            district: "srodmiescie",
            coordinate_precision: "building",
            confidence: "high",
          },
          development: null,
          field_confidence: [],
          media: [],
          source_message_id: null,
          verified_source_url: null,
          source_history: [],
        });
      }
      throw new Error(url.pathname);
    });

    expect((await fetchQuickFilters({ fetcher })).state).toBe("ready");
    expect((await fetchOfferDetail("missing", { fetcher })).state).toBe(
      "not_found",
    );
    expect((await fetchOfferDetail("ready", { fetcher })).state).toBe("ready");
  });

  it("normalizes complete map coordinates", async () => {
    const fetcher = vi.fn(async () =>
      response({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            id: "10000000-0000-4000-8000-000000000001",
            geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
            properties: {
              display_name: "Synthetic Central Residence",
              display_address: "Synthetic address",
              district: "srodmiescie",
              coordinate_precision: "building",
              confidence: "high",
              matching_offer_count: 1,
              total_offer_count: 1,
              latest_published_at: "2026-08-01T10:00:00Z",
              price_min_minor: null,
              price_max_minor: null,
              area_min_sqm: null,
              area_max_sqm: null,
              currency: "PLN",
            },
          },
        ],
        meta: {
          request_id: "00000000-0000-4000-8000-000000000001",
          feature_count: 1,
          matching_offer_count: 1,
        },
      }),
    );
    const result = await fetchLocationMap({ bbox: DEFAULT_BBOX }, { fetcher });
    expect(result.state).toBe("ready");
    if (result.state === "ready") {
      expect(result.data.features[0]?.geometry.coordinates).toEqual([
        21.0122, 52.2297,
      ]);
    }
  });

  it("rejects map features with incomplete coordinates", async () => {
    const fetcher = vi.fn(async () =>
      response({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            id: "broken",
            geometry: { type: "Point", coordinates: [21.0] },
            properties: {},
          },
        ],
        meta: {
          request_id: "00000000-0000-4000-8000-000000000001",
          feature_count: 1,
          matching_offer_count: 0,
        },
      }),
    );

    expect(
      (await fetchLocationMap({ bbox: DEFAULT_BBOX }, { fetcher })).state,
    ).toBe("error");
  });

  it("treats empty successful payloads as errors", async () => {
    const empty = vi.fn(async () => new Response(null, { status: 200 }));
    expect((await fetchQuickFilters({ fetcher: empty })).state).toBe("error");
    expect((await fetchFacets({ fetcher: empty })).state).toBe("error");
    expect(
      (
        await fetchLocationOffers(
          "10000000-0000-4000-8000-000000000001",
          { bbox: DEFAULT_BBOX },
          { fetcher: empty },
        )
      ).state,
    ).toBe("error");
    expect(
      (await fetchLocationMap({ bbox: DEFAULT_BBOX }, { fetcher: empty }))
        .state,
    ).toBe("error");
  });

  it("returns a stable error when the catalog client throws", async () => {
    const offline = vi.fn(async () => {
      throw new Error("offline");
    });
    expect((await fetchQuickFilters({ fetcher: offline })).state).toBe("error");
    expect((await fetchFacets({ fetcher: offline })).state).toBe("error");
    expect(
      (
        await fetchLocationOffers(
          "10000000-0000-4000-8000-000000000001",
          { bbox: DEFAULT_BBOX },
          { fetcher: offline },
        )
      ).state,
    ).toBe("error");
    expect((await fetchOfferDetail("ready", { fetcher: offline })).state).toBe(
      "error",
    );
  });
});
