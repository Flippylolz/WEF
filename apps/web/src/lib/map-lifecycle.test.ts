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
});
