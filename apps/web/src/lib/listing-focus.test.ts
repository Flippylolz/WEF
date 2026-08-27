import { describe, expect, it } from "vitest";

import { isWithinComfortRegion } from "@/lib/listing-focus";

const bounds = {
  getWest: () => 20.8,
  getSouth: () => 52.1,
  getEast: () => 21.2,
  getNorth: () => 52.4,
};

describe("isWithinComfortRegion", () => {
  it("accepts a point near the viewport center", () => {
    expect(isWithinComfortRegion(bounds, [21.0, 52.25])).toBe(true);
  });

  it("rejects a point inside the map but inside the comfort padding", () => {
    expect(isWithinComfortRegion(bounds, [20.83, 52.13])).toBe(false);
    expect(isWithinComfortRegion(bounds, [21.17, 52.37])).toBe(false);
  });

  it("rejects a point outside the viewport", () => {
    expect(isWithinComfortRegion(bounds, [19.0, 50.0])).toBe(false);
  });

  it("handles a flat viewport without dividing by a negative span", () => {
    const flat = {
      getWest: () => 21.0,
      getSouth: () => 52.2,
      getEast: () => 21.0,
      getNorth: () => 52.2,
    };
    expect(isWithinComfortRegion(flat, [21.0, 52.2])).toBe(false);
  });
});
