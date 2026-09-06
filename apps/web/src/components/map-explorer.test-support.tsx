import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState, type ComponentType } from "react";
import { afterEach, beforeEach, vi } from "vitest";

import { MapExplorer } from "@/components/map-explorer";
import * as authApi from "@/lib/auth-api";
import * as catalogApi from "@/lib/catalog-api";
import * as favoritesApi from "@/lib/favorites-api";
import * as viewHistoryApi from "@/lib/view-history-api";

const navigation = vi.hoisted(() => ({
  listeners: new Set<() => void>(),
  pathname: "/",
  push: vi.fn(),
  replace: vi.fn(),
  search: "",
}));

vi.mock("next-intl", () => ({
  useTranslations:
    () =>
    (
      key: string,
      values?: { count?: number; room?: number; label?: string },
    ) => {
      if (values?.count !== undefined) return `${key}:${values.count}`;
      if (values?.room !== undefined) return `${key}:${values.room}`;
      if (values?.label !== undefined) return `${key}:${values.label}`;
      return key;
    },
}));

vi.mock("next/navigation", async () => {
  const { useSyncExternalStore } =
    await vi.importActual<typeof import("react")>("react");
  return {
    usePathname: () => navigation.pathname,
    useRouter: () => ({
      push: navigation.push,
      replace: navigation.replace,
    }),
    useSearchParams: () => {
      const search = useSyncExternalStore(
        (listener) => {
          navigation.listeners.add(listener);
          return () => navigation.listeners.delete(listener);
        },
        () => navigation.search,
        () => navigation.search,
      );
      return new URLSearchParams(search);
    },
  };
});

const mapMountCount = vi.hoisted(() => ({ value: 0 }));

vi.mock("next/dynamic", () => ({
  default: (
    loader: () => Promise<{
      WarsawMap?: unknown;
      OfferDetailDrawer?: unknown;
      default?: unknown;
    }>,
  ) => {
    function FakeMap({
      onFailure,
      onSelect,
      onViewportChange,
    }: {
      onFailure: () => void;
      onSelect: (locationId: string) => void;
      onViewportChange: (bbox: string) => void;
    }) {
      useEffect(() => {
        mapMountCount.value += 1;
      }, []);

      return (
        <div data-testid="map">
          <button type="button" onClick={onFailure}>
            fail-map
          </button>
          <button
            type="button"
            onClick={() => onSelect("10000000-0000-4000-8000-000000000001")}
          >
            select-pin
          </button>
          <button
            type="button"
            onClick={() => onViewportChange("20.8,52.1,21.2,52.3")}
          >
            move-map
          </button>
          <button
            type="button"
            onClick={() => onViewportChange("20.7,52.0,21.4,52.4")}
          >
            return-map
          </button>
        </div>
      );
    }

    if (loader.toString().includes("warsaw-map")) {
      return FakeMap;
    }

    return function DynamicComponent(props: Record<string, unknown>) {
      const [Resolved, setResolved] = useState<ComponentType<
        Record<string, unknown>
      > | null>(null);

      useEffect(() => {
        void loader().then((module) => {
          const candidate =
            typeof module === "function"
              ? module
              : "OfferDetailDrawer" in module
                ? module.OfferDetailDrawer
                : module.default;
          setResolved(
            () => candidate as ComponentType<Record<string, unknown>>,
          );
        });
      }, []);

      if (!Resolved) return null;
      return <Resolved {...props} />;
    };
  },
}));

export function renderExplorer() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MapExplorer />
    </QueryClientProvider>,
  );
}

export async function openFiltersDrawer(
  user: ReturnType<typeof userEvent.setup>,
) {
  await user.click(screen.getByRole("button", { name: /^filtersButton/ }));
}

export function setNavigationHref(target: string) {
  const url = new URL(target, "http://example.test");
  navigation.pathname = url.pathname;
  navigation.search = url.search.slice(1);
  for (const listener of navigation.listeners) listener();
}

export const mapData: catalogApi.LocationMap = {
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

export const facets: catalogApi.FilterFacets = {
  districts: ["srodmiescie"],
  rooms: [1, 2, 3],
  market_types: ["primary"],
  content_types: ["development"],
  property_types: [],
  price_min_minor: 80_000_000,
  price_max_minor: 125_000_000,
  area_min_sqm: "35.00",
  area_max_sqm: "71.50",
  published_from: "2026-08-01T10:00:00Z",
  published_to: "2026-08-01T10:00:00Z",
};

export const listingPage: catalogApi.ViewportListingPage = {
  items: [
    {
      id: "20000000-0000-4000-8000-000000000009",
      content_type: "development",
      market_type: "primary",
      property_type: "unknown",
      display_name: "development · primary",
      data_confidence: "complete",
      data_origin: "parser",
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
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "low",
        geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
      },
    },
  ],
  matching_count: 1,
  next_cursor: null,
};

export const offerPage: catalogApi.LocationOfferPage = {
  items: [
    {
      id: "20000000-0000-4000-8000-000000000001",
      content_type: "development",
      market_type: "primary",
      property_type: "unknown",
      display_name: "development · primary",
      data_confidence: "complete",
      data_origin: "parser",
      published_at: "2026-08-01T10:00:00Z",
      currency: "PLN",
      price_min_minor: 80_000_000,
      price_max_minor: 125_000_000,
      parking_price_min_minor: 4_500_000,
      parking_price_max_minor: 4_500_000,
      parking_included_in_price: false,
      storage_price_min_minor: null,
      storage_price_max_minor: null,
      storage_included_in_price: true,
      area_min_sqm: "35.00",
      area_max_sqm: "71.50",
      rooms_min: 1,
      rooms_max: 3,
      floor_label: null,
      delivery_label: "Synthetic delivery",
      matches_filters: true,
    },
  ],
  matching_count: 1,
  total_count: 2,
  next_cursor: null,
};

export function setupMapExplorer() {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    mapMountCount.value = 0;
    navigation.pathname = "/";
    navigation.search = "";
    navigation.listeners.clear();
    navigation.push.mockReset();
    navigation.replace.mockReset();
    navigation.push.mockImplementation(setNavigationHref);
    navigation.replace.mockImplementation(setNavigationHref);
    vi.spyOn(catalogApi, "fetchLocationMap").mockResolvedValue({
      state: "ready",
      data: mapData,
    });
    vi.spyOn(catalogApi, "fetchFacets").mockResolvedValue({
      state: "ready",
      data: facets,
    });
    vi.spyOn(catalogApi, "fetchQuickFilters").mockResolvedValue({
      state: "ready",
      data: { items: [{ id: "last_day", label_key: "quickFilter.last_day" }] },
    });
    vi.spyOn(catalogApi, "fetchLocationOffers").mockResolvedValue({
      state: "ready",
      data: offerPage,
    });
    vi.spyOn(catalogApi, "fetchViewportListings").mockResolvedValue({
      state: "ready",
      data: listingPage,
    });
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "error",
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: { items: [] },
    });
    vi.spyOn(viewHistoryApi, "startAccountVisit").mockResolvedValue({
      state: "error",
    });
    vi.spyOn(viewHistoryApi, "markOfferViewed").mockResolvedValue({
      state: "error",
    });
  });
}

export { navigation, mapMountCount };
