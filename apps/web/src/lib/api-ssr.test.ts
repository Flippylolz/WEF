/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCurrentAccount } from "@/lib/auth-api";
import { fetchFacets } from "@/lib/catalog-api";
import { revealOfferContacts } from "@/lib/contacts-api";
import { fetchFavorites } from "@/lib/favorites-api";
import { startWebVitalsCollection } from "@/lib/web-vitals";

describe("API clients without a window", () => {
  afterEach(() => {
    delete process.env.WEF_API_URL;
  });

  it("uses WEF_API_URL when the browser origin is unavailable", async () => {
    process.env.WEF_API_URL = " http://api.example.test ";
    const seen: string[] = [];
    const fetcher = vi.fn(async (request: Request) => {
      seen.push(request.url);
      return new Response("{}", { status: 503 });
    });

    await fetchFacets({ fetcher });
    await fetchCurrentAccount({ fetcher });
    await fetchFavorites({ fetcher });
    await revealOfferContacts("20000000-0000-4000-8000-000000000001", {
      fetcher,
    });

    expect(
      seen.every((url) => url.startsWith("http://api.example.test/")),
    ).toBe(true);
  });

  it("falls back to the local API when WEF_API_URL is empty", async () => {
    process.env.WEF_API_URL = "  ";
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.url.startsWith("http://127.0.0.1:8000/")).toBe(true);
      return new Response("{}", { status: 503 });
    });
    await fetchFacets({ fetcher });
    await fetchCurrentAccount({ fetcher });
    await fetchFavorites({ fetcher });
    await revealOfferContacts("20000000-0000-4000-8000-000000000001", {
      fetcher,
    });
  });

  it("does not start web-vitals collection without a window", () => {
    expect(() => startWebVitalsCollection()).not.toThrow();
  });
});
