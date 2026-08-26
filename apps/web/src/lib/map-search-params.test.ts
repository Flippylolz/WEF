import { describe, expect, it } from "vitest";

import {
  boundedWarsawViewport,
  DEFAULT_BBOX,
  DEFAULT_MAP_SEARCH_STATE,
  formatBbox,
  normalizeBbox,
  parseMapSearchParams,
  serializeMapSearchState,
  toMapLocationQuery,
} from "@/lib/map-search-params";

describe("map search parameters", () => {
  it("omits the default Warsaw viewport and both content types", () => {
    expect(serializeMapSearchState(DEFAULT_MAP_SEARCH_STATE)).toBe("");
    expect(toMapLocationQuery(DEFAULT_MAP_SEARCH_STATE)).toEqual({
      bbox: DEFAULT_BBOX,
    });
  });

  it("round-trips every M1 filter in one deterministic order", () => {
    const source = new URLSearchParams(
      "rooms=3&district=wola&content_type=unit&price_max=125000000" +
        "&market_type=secondary&area_max=71.5&published_to=2026-08-31T23%3A59%3A59.999Z" +
        "&rooms=1&district=ochota&price_min=80000000&area_min=35" +
        "&published_from=2026-08-01T00%3A00%3A00.000Z&bbox=20.8%2C52.1%2C21.2%2C52.3",
    );

    const state = parseMapSearchParams(source);

    expect(serializeMapSearchState(state)).toBe(
      "bbox=20.8%2C52.1%2C21.2%2C52.3&price_min=80000000&price_max=125000000" +
        "&area_min=35&area_max=71.5&rooms=1&rooms=3&district=ochota&district=wola" +
        "&market_type=secondary&content_type=unit" +
        "&published_from=2026-08-01T00%3A00%3A00.000Z" +
        "&published_to=2026-08-31T23%3A59%3A59.999Z",
    );
    expect(toMapLocationQuery(state)).toEqual({
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
    });
  });

  it("normalizes repeats and safely falls back for invalid syntax", () => {
    const state = parseMapSearchParams(
      new URLSearchParams(
        "bbox=invalid&rooms=2&rooms=bad&rooms=2&market_type=invalid" +
          "&content_type=invalid&area_min=not-a-number&price_min=1.5" +
          "&published_from=2026-02-30T00%3A00%3A00Z",
      ),
    );

    expect(state).toMatchObject({
      bbox: DEFAULT_BBOX,
      rooms: [2],
      marketTypes: [],
      contentTypes: ["development", "unit"],
      areaMin: null,
      priceMinMinor: null,
      publishedFrom: null,
    });

    expect(
      parseMapSearchParams(new URLSearchParams("bbox=1,2,3,foo")).bbox,
    ).toBe(DEFAULT_BBOX);
    expect(
      parseMapSearchParams(new URLSearchParams("published_from=yesterday"))
        .publishedFrom,
    ).toBeNull();
    expect(
      parseMapSearchParams(
        new URLSearchParams("published_from=2026-08-01T25:00:00Z"),
      ).publishedFrom,
    ).toBeNull();
  });

  it("canonicalizes equivalent publication timestamps in UTC", () => {
    const state = parseMapSearchParams(
      new URLSearchParams(
        "published_from=2026-08-01T02%3A00%3A00%2B02%3A00" +
          "&published_to=2026-08-31",
      ),
    );

    expect(state.publishedFrom).toBe("2026-08-01T00:00:00.000Z");
    expect(state.publishedTo).toBe("2026-08-31T23:59:59.999Z");
  });

  it("uses six-decimal viewport identity without changing the default", () => {
    expect(normalizeBbox("20.700000,52,21.400000,52.400000")).toBe(
      DEFAULT_BBOX,
    );
    expect(formatBbox([20.81234549, 52.12345651, 21.2, 52.3])).toBe(
      "20.812345,52.123457,21.2,52.3",
    );
    expect(boundedWarsawViewport([19, 51, 23, 54])).toBe(
      "20.6505,51.8005,21.4495,52.5995",
    );
  });

  it("never emits a viewport span the backend query limit rejects", () => {
    // Regression: an exact 0.8 span round-trips through the six-decimal
    // bbox string as 0.8000000000000007 and the API answers 422.
    const bounded = boundedWarsawViewport([
      20.649911, 52.092717, 21.449911, 52.323579,
    ]);
    const [west, south, east, north] = bounded
      .split(",")
      .map((part) => Number(part));

    expect(east - west).toBeLessThanOrEqual(0.8);
    expect(north - south).toBeLessThanOrEqual(0.8);
  });
});
