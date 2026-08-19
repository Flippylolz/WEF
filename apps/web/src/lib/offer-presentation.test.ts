import { describe, expect, it } from "vitest";

import {
  formatAdditionalPrice,
  formatArea,
  formatPrice,
  formatPublishedDate,
  isSafeExternalUrl,
  mediaAltText,
  pickMediaDisplayUrl,
} from "@/lib/offer-presentation";

describe("offer-presentation", () => {
  it("formats prices and areas without inventing values", () => {
    expect(formatPrice(80_000_000, 80_000_000)).toContain("800");
    expect(formatPrice(null, 80_000_000)).toBeNull();
    expect(formatAdditionalPrice(1_000_000, 1_000_000, true, "Included")).toBe(
      "Included",
    );
    expect(formatArea("35.00", "71.50")).toBe("35.00–71.50 m²");
    expect(formatArea(null, "71.50")).toBeNull();
  });

  it("accepts only verified https source links", () => {
    expect(isSafeExternalUrl("https://t.me/elestate_warszawa/42")).toBe(true);
    expect(isSafeExternalUrl("http://example.test/offer")).toBe(false);
    expect(isSafeExternalUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeExternalUrl(null)).toBe(false);
  });

  it("builds media alt text and prefers content urls", () => {
    expect(
      mediaAltText(
        {
          display_name: "unit · secondary",
          location: {
            id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address",
            district: "srodmiescie",
            coordinate_precision: "building",
            confidence: "high",
          },
        },
        0,
        2,
      ),
    ).toContain("media 1 of 2");
    expect(pickMediaDisplayUrl("/media/thumb.webp", "/media/full.jpg")).toBe(
      "/media/full.jpg",
    );
    expect(pickMediaDisplayUrl("/media/thumb.webp", null)).toBe(
      "/media/thumb.webp",
    );
  });

  it("formats publication timestamps deterministically", () => {
    expect(formatPublishedDate("2026-08-01T10:00:00Z")).toContain("2026");
  });
});
