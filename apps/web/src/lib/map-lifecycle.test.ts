import { afterEach, describe, expect, it } from "vitest";

import {
  getMapConstructionCount,
  recordMapConstruction,
  resetMapConstructionCount,
} from "@/lib/map-lifecycle";

describe("map-lifecycle", () => {
  afterEach(() => {
    resetMapConstructionCount();
  });

  it("tracks construction count only in test mode", () => {
    expect(getMapConstructionCount()).toBe(0);
    recordMapConstruction();
    expect(getMapConstructionCount()).toBe(1);
    resetMapConstructionCount();
    expect(getMapConstructionCount()).toBe(0);
  });

  it("does not count constructions outside test mode", () => {
    const previous = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";
    try {
      recordMapConstruction();
      expect(getMapConstructionCount()).toBe(0);
    } finally {
      process.env.NODE_ENV = previous;
    }
  });
});
