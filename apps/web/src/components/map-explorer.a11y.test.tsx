import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "vitest-axe";
import { describe, expect, it, vi } from "vitest";

import { MapExplorer } from "@/components/map-explorer";
import * as authApi from "@/lib/auth-api";
import * as catalogApi from "@/lib/catalog-api";
import * as favoritesApi from "@/lib/favorites-api";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: { count?: number; name?: string }) => {
      if (values?.count !== undefined) return `${key}:${values.count}`;
      if (values?.name !== undefined) return `${key}:${values.name}`;
      return key;
    },
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/dynamic", () => ({
  default: () =>
    function FakeMap() {
      return <div data-testid="map" />;
    },
}));

const mapData: catalogApi.LocationMap = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "10000000-0000-4000-8000-000000000001",
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
      properties: {
        display_name: "Synthetic Central Residence",
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "low",
        matching_offer_count: 1,
        total_offer_count: 2,
        latest_published_at: "2026-08-01T10:00:00Z",
        price_min_minor: 80_000_000,
        price_max_minor: 125_000_000,
        area_min_sqm: "35.00",
        area_max_sqm: "71.50",
        currency: "PLN",
      },
    },
  ],
  meta: {
    request_id: "00000000-0000-4000-8000-000000000001",
    feature_count: 1,
    matching_offer_count: 1,
  },
};

describe("MapExplorer accessibility", () => {
  it("has no axe violations on the initial explorer shell", async () => {
    vi.spyOn(catalogApi, "fetchLocationMap").mockResolvedValue({
      state: "ready",
      data: mapData,
    });
    vi.spyOn(catalogApi, "fetchFacets").mockResolvedValue({
      state: "ready",
      data: {
        districts: ["srodmiescie"],
        rooms: [1, 2],
        market_types: ["primary"],
        content_types: ["development"],
        price_min_minor: 80_000_000,
        price_max_minor: 125_000_000,
        area_min_sqm: "35.00",
        area_max_sqm: "71.50",
        published_from: "2026-08-01T10:00:00Z",
        published_to: "2026-08-01T10:00:00Z",
      },
    });
    vi.spyOn(catalogApi, "fetchQuickFilters").mockResolvedValue({
      state: "ready",
      data: { items: [] },
    });
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "error",
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: { items: [] },
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <MapExplorer />
      </QueryClientProvider>,
    );

    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});
