import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { useEffect, useState, type ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MapExplorer } from "@/components/map-explorer";
import * as authApi from "@/lib/auth-api";
import * as catalogApi from "@/lib/catalog-api";
import * as favoritesApi from "@/lib/favorites-api";
import { lastVisitStorageKeys } from "@/lib/last-visit";
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

function renderExplorer() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MapExplorer />
    </QueryClientProvider>,
  );
}

async function openFiltersDrawer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /^filtersButton/ }));
}

function setNavigationHref(target: string) {
  const url = new URL(target, "http://example.test");
  navigation.pathname = url.pathname;
  navigation.search = url.search.slice(1);
  for (const listener of navigation.listeners) listener();
}

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

const facets: catalogApi.FilterFacets = {
  districts: ["srodmiescie"],
  rooms: [1, 2, 3],
  market_types: ["primary"],
  content_types: ["development"],
  price_min_minor: 80_000_000,
  price_max_minor: 125_000_000,
  area_min_sqm: "35.00",
  area_max_sqm: "71.50",
  published_from: "2026-08-01T10:00:00Z",
  published_to: "2026-08-01T10:00:00Z",
};

const listingPage: catalogApi.ViewportListingPage = {
  items: [
    {
      id: "20000000-0000-4000-8000-000000000009",
      content_type: "development",
      market_type: "primary",
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

const offerPage: catalogApi.LocationOfferPage = {
  items: [
    {
      id: "20000000-0000-4000-8000-000000000001",
      content_type: "development",
      market_type: "primary",
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

describe("MapExplorer", () => {
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

  it("keeps an accessible list and opens backend offer summaries", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.fetchLocationOffers).mockResolvedValue({
      state: "ready",
      data: {
        ...offerPage,
        items: [
          ...offerPage.items,
          {
            ...offerPage.items[0]!,
            id: "20000000-0000-4000-8000-000000000002",
            display_name: "Older related post",
            matches_filters: false,
          },
        ],
      },
    });
    renderExplorer();

    const location = await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    expect(screen.getByText("lowConfidence")).toBeInTheDocument();

    await user.click(location);

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("apartmentPrice")).toHaveLength(2);
    expect(screen.getAllByText("parkingPrice")).toHaveLength(2);
    expect(screen.getAllByText("storagePrice")).toHaveLength(2);
    expect(screen.getAllByText("includedInApartmentPrice")).toHaveLength(2);
    expect(screen.getByText("nonMatchingOffer")).toBeInTheDocument();
    expect(screen.getByText("offerCountSummary")).toBeInTheDocument();
    expect(catalogApi.fetchLocationOffers).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
      { bbox: catalogApi.DEFAULT_BBOX },
      { signal: expect.any(AbortSignal) },
    );
  });

  it("falls back to the semantic list when the map fails", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    await user.click(screen.getByRole("button", { name: "fail-map" }));

    await waitFor(() => {
      expect(screen.getByText("mapUnavailable")).toBeInTheDocument();
      expect(
        screen.getByRole("button", {
          name: /Synthetic Central Residence/,
        }),
      ).toBeInTheDocument();
    });
  });

  it("announces API failures without mounting a broken map", async () => {
    vi.mocked(catalogApi.fetchLocationMap).mockResolvedValue({
      state: "error",
    });
    renderExplorer();

    const filtersToggle = screen.getByRole("button", {
      name: /^filtersButton/,
    });
    expect(filtersToggle).toHaveAttribute("aria-haspopup", "dialog");
    expect(screen.getAllByText("loading").length).toBeGreaterThan(0);
    const errors = await screen.findAllByText("error");
    expect(
      errors.some((error) => error.closest('[role="alert"]') !== null),
    ).toBe(true);
    const user = userEvent.setup();
    await openFiltersDrawer(user);
    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
    expect(screen.queryByTestId("map")).not.toBeInTheDocument();
  });

  it("announces an empty viewport projection with clear-and-reset actions", async () => {
    vi.mocked(catalogApi.fetchViewportListings).mockResolvedValue({
      state: "ready",
      data: { items: [], matching_count: 0, next_cursor: null },
    });
    renderExplorer();

    const emptyMessage = await screen.findByText("listingsEmpty");
    expect(emptyMessage.closest('[role="status"]')).not.toBeNull();
    expect(screen.getByRole("button", { name: "clearFilters" })).toBeVisible();
    expect(screen.getByRole("button", { name: "resetMap" })).toBeVisible();
  });

  it("restores a combined URL filter query and clears to Warsaw defaults", async () => {
    navigation.search =
      "price_min=80000000&price_max=125000000&area_min=35&area_max=71.5" +
      "&rooms=2&district=wola&market_type=secondary&content_type=unit" +
      "&published_from=2026-08-01T00%3A00%3A00.000Z" +
      "&published_to=2026-08-31T23%3A59%3A59.999Z";
    renderExplorer();

    await waitFor(() => {
      expect(catalogApi.fetchLocationMap).toHaveBeenCalledWith(
        {
          bbox: catalogApi.DEFAULT_BBOX,
          price_min: 80_000_000,
          price_max: 125_000_000,
          area_min: "35",
          area_max: "71.5",
          rooms: [2],
          district: ["wola"],
          market_type: ["secondary"],
          content_type: ["unit"],
          published_from: "2026-08-01T00:00:00.000Z",
          published_to: "2026-08-31T23:59:59.999Z",
        },
        { signal: expect.any(AbortSignal) },
      );
    });

    const user = userEvent.setup();
    await openFiltersDrawer(user);
    expect(
      screen.getByRole("checkbox", { name: "roomOption:2" }),
    ).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Wola" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "clearFilters" }));
    expect(navigation.push).toHaveBeenCalledWith("/", { scroll: false });
    await waitFor(() => {
      expect(catalogApi.fetchLocationMap).toHaveBeenLastCalledWith(
        { bbox: catalogApi.DEFAULT_BBOX },
        { signal: expect.any(AbortSignal) },
      );
    });
    expect(navigation.search).toBe("");
    await openFiltersDrawer(user);
    expect(
      screen.getByRole("checkbox", { name: "roomOption:2" }),
    ).not.toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "contentType.development" }),
    ).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "contentType.unit" }),
    ).toBeChecked();
  });

  it("debounces viewport URL replacement", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    vi.useFakeTimers();

    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(299));
    expect(navigation.replace).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "return-map" }));
    act(() => vi.advanceTimersByTime(1));
    expect(navigation.replace).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));
    expect(navigation.replace).toHaveBeenCalledWith(
      "/?bbox=20.8%2C52.1%2C21.2%2C52.3",
      { scroll: false },
    );
    expect(navigation.search).toBe("bbox=20.8%2C52.1%2C21.2%2C52.3");

    navigation.replace.mockReset();
    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  it("aborts the obsolete map request when URL state changes", async () => {
    let firstSignal: AbortSignal | undefined;
    vi.mocked(catalogApi.fetchLocationMap).mockImplementation(
      (query, options) => {
        if (query === undefined) throw new Error("expected map query");
        if (query.bbox !== catalogApi.DEFAULT_BBOX) {
          return Promise.resolve({ state: "ready", data: mapData });
        }
        return new Promise((resolve) => {
          firstSignal = options?.signal;
          options?.signal?.addEventListener(
            "abort",
            () => resolve({ state: "error" }),
            { once: true },
          );
        });
      },
    );
    renderExplorer();
    await waitFor(() => expect(firstSignal).toBeDefined());

    act(() => setNavigationHref("/?bbox=20.8%2C52.1%2C21.2%2C52.3"));

    await waitFor(() => expect(firstSignal?.aborted).toBe(true));
    expect(catalogApi.fetchLocationMap).toHaveBeenLastCalledWith(
      { bbox: "20.8,52.1,21.2,52.3" },
      { signal: expect.any(AbortSignal) },
    );
  });

  it("hides the sidebar and reopens it with data when a pin is selected", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    const sidebar = document.getElementById("explorer-sidebar");
    expect(sidebar).not.toBeNull();
    expect(sidebar).not.toHaveAttribute("inert");

    await user.click(screen.getByRole("button", { name: "hidePanel" }));

    // the panel stays mounted for the collapse animation but is inert
    expect(sidebar).toHaveAttribute("inert");
    const show = screen.getByRole("button", { name: "showPanel" });
    expect(show).toHaveAttribute("aria-expanded", "false");
    expect(show.querySelector("svg")).not.toBeNull();
    expect(
      screen.getByRole("button", { name: "hidePanel" }).querySelector("svg"),
    ).not.toBeNull();

    await user.click(show);
    expect(sidebar).not.toHaveAttribute("inert");

    await user.click(screen.getByRole("button", { name: "select-pin" }));

    expect(sidebar).not.toHaveAttribute("inert");
    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
  });

  it("keeps filter drafts across viewport updates and preserves the view on apply", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    const user = userEvent.setup();
    await openFiltersDrawer(user);
    fireEvent.change(screen.getByRole("spinbutton", { name: "minimumPrice" }), {
      target: { value: "800000" },
    });
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));

    expect(navigation.search).toBe("bbox=20.8%2C52.1%2C21.2%2C52.3");
    expect(
      screen.getByRole("spinbutton", { name: "minimumPrice" }),
    ).toHaveValue(800000);

    navigation.push.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "applyFilters" }));

    expect(navigation.push).toHaveBeenCalledWith(
      "/?bbox=20.8%2C52.1%2C21.2%2C52.3&price_min=80000000",
      { scroll: false },
    );
  });

  it("aborts an obsolete map request on unmount", async () => {
    let observedSignal: AbortSignal | undefined;
    vi.mocked(catalogApi.fetchLocationMap).mockImplementation(
      (_query, options) =>
        new Promise((resolve) => {
          observedSignal = options?.signal;
          options?.signal?.addEventListener(
            "abort",
            () => resolve({ state: "error" }),
            { once: true },
          );
        }),
    );

    const view = renderExplorer();
    await waitFor(() => expect(observedSignal).toBeDefined());
    view.unmount();

    expect(observedSignal?.aborted).toBe(true);
  });

  it("loads offer detail after explicit offer selection", async () => {
    const user = userEvent.setup();
    const offerDetail: catalogApi.OfferDetail = {
      id: "20000000-0000-4000-8000-000000000001",
      content_type: "development",
      market_type: "primary",
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
      public_source_text: "Masked public text only.",
      parser_version: "synthetic-m1-v1",
      location: {
        id: "10000000-0000-4000-8000-000000000001",
        display_name: "Synthetic Central Residence",
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "low",
      },
      development: null,
      field_confidence: [],
      media: [],
      source_message_id: null,
      verified_source_url: null,
      source_history: [],
    };
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: offerDetail,
    });
    renderExplorer();
    await user.click(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: /viewOfferDetails/,
      }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("offer-detail-overlay")).toBeInTheDocument();
    });
    expect(screen.getByText("Masked public text only.")).toBeInTheDocument();
    expect(catalogApi.fetchOfferDetail).toHaveBeenCalledWith(
      "20000000-0000-4000-8000-000000000001",
      { signal: expect.any(AbortSignal) },
    );
    await user.click(
      screen.getByRole("button", { name: "detailRevealSignInAction" }),
    );
    expect(await screen.findByText("loginTitle")).toBeInTheDocument();
    await user.click(screen.getByText("detailClose"));
    await waitFor(() => {
      expect(
        screen.queryByTestId("offer-detail-overlay"),
      ).not.toBeInTheDocument();
    });
  });

  it("opens the mobile sheet and password prompt from a selected offer", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("max-width: 56rem"),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      })),
    );
    vi.mocked(authApi.fetchCurrentAccount).mockResolvedValue({
      state: "ready",
      data: {
        id: "00000000-0000-4000-8000-000000000001",
        username: "warsaw",
        role: "user",
        must_change_password: true,
        created_at: "2026-01-01T00:00:00Z",
        last_login_at: null,
      },
    });
    const offerDetail: catalogApi.OfferDetail = {
      id: "20000000-0000-4000-8000-000000000001",
      content_type: "development",
      market_type: "primary",
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
      floor_label: "3",
      delivery_label: "Synthetic delivery",
      public_source_text: "Masked public text only.",
      parser_version: "synthetic-m1-v1",
      location: {
        id: "10000000-0000-4000-8000-000000000001",
        display_name: "Synthetic Central Residence",
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "high",
      },
      development: null,
      field_confidence: [],
      media: [],
      source_message_id: null,
      verified_source_url: "https://t.me/elestate_warszawa/42",
      source_history: [],
    };
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: offerDetail,
    });
    renderExplorer();

    expect(await screen.findByText("mobileShowListings:1")).toBeInTheDocument();
    await user.click(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    );
    expect(await screen.findByText("mobileShowMap")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: /viewOfferDetails/,
      }),
    );
    await user.click(
      await screen.findByRole("button", { name: "detailRevealPasswordAction" }),
    );
    await waitFor(() => {
      expect(viewHistoryApi.markOfferViewed).toHaveBeenCalledWith(
        "20000000-0000-4000-8000-000000000001",
      );
    });
    expect(await screen.findByText("forcedPasswordTitle")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "mobileFullList" }));
    expect(
      screen.getByRole("button", { name: "mobileShowMap" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "mobileShowMap" }));
    expect(screen.getByText("mobileShowListings:1")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("does not fetch offer detail before explicit offer selection", async () => {
    const fetchOfferDetail = vi.spyOn(catalogApi, "fetchOfferDetail");
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    expect(fetchOfferDetail).not.toHaveBeenCalled();
  });

  it("keeps a single map mount across viewport and filter changes", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await screen.findByTestId("map");
    expect(mapMountCount.value).toBe(1);

    await user.click(screen.getByRole("button", { name: "move-map" }));
    await waitFor(() => expect(navigation.replace).toHaveBeenCalled());
    expect(mapMountCount.value).toBe(1);

    await user.click(screen.getByRole("button", { name: "return-map" }));
    await waitFor(() =>
      expect(navigation.replace.mock.calls.length).toBeGreaterThan(1),
    );
    expect(mapMountCount.value).toBe(1);
  });

  it("retries the map after a load failure without losing the list", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    await user.click(screen.getByRole("button", { name: "fail-map" }));
    expect(await screen.findByText("mapUnavailable")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "retryMap" }));

    await waitFor(() => {
      expect(screen.getByTestId("map")).toBeInTheDocument();
    });
    expect(mapMountCount.value).toBe(2);
    expect(
      screen.getByRole("button", { name: /Synthetic Central Residence/ }),
    ).toBeInTheDocument();
  });

  it("stars and unstars a location for a signed-in account", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.fetchCurrentAccount).mockResolvedValue({
      state: "ready",
      data: {
        id: "00000000-0000-4000-8000-000000000001",
        username: "warsaw",
        role: "user",
        must_change_password: false,
        created_at: "2026-01-01T00:00:00Z",
        last_login_at: null,
      },
    });
    vi.mocked(favoritesApi.fetchFavorites)
      .mockResolvedValueOnce({ state: "ready", data: { items: [] } })
      .mockResolvedValue({
        state: "ready",
        data: {
          items: [
            {
              location_id: "10000000-0000-4000-8000-000000000001",
              display_name: "Synthetic Central Residence",
              display_address: "Synthetic address, Warsaw",
              district: "srodmiescie",
              created_at: "2026-08-20T12:00:00+00:00",
            },
          ],
        },
      });
    vi.spyOn(favoritesApi, "addFavorite").mockResolvedValue({
      state: "ready",
      data: null,
    });
    vi.spyOn(favoritesApi, "removeFavorite").mockResolvedValue({
      state: "ready",
      data: null,
    });
    renderExplorer();

    const star = await screen.findByRole("button", { name: "starLocation" });
    await user.click(star);
    expect(favoritesApi.addFavorite).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    const unstar = await screen.findByRole("button", {
      name: "unstarLocation",
    });
    await user.click(unstar);
    expect(favoritesApi.removeFavorite).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
  });

  it("retries after an offer list error and shows an empty offer list", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.fetchLocationOffers)
      .mockResolvedValueOnce({ state: "error" })
      .mockResolvedValueOnce({
        state: "ready",
        data: {
          items: [],
          matching_count: 0,
          total_count: 0,
          next_cursor: null,
        },
      });
    renderExplorer();

    await user.click(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    );
    expect(await screen.findByText("offersError")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "retry" }));
    expect(await screen.findByText("offersEmpty")).toBeInTheDocument();
  });

  it("retries a failed offer detail request after explicit selection", async () => {
    const user = userEvent.setup();
    vi.spyOn(catalogApi, "fetchOfferDetail")
      .mockResolvedValueOnce({ state: "error" })
      .mockResolvedValueOnce({
        state: "ready",
        data: {
          id: "20000000-0000-4000-8000-000000000001",
          content_type: "development",
          market_type: "primary",
          display_name: "development · primary",
          data_confidence: "partial",
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
          floor_label: "3",
          delivery_label: "Synthetic delivery",
          public_source_text: "Masked public text only.",
          parser_version: "synthetic-m1-v1",
          location: {
            id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            coordinate_precision: "district",
            confidence: "high",
          },
          development: null,
          field_confidence: [],
          media: [],
          source_message_id: null,
          verified_source_url: "http://example.test/offer",
          source_history: [],
        },
      });
    renderExplorer();
    await user.click(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: /viewOfferDetails/,
      }),
    );
    expect(await screen.findByText("detailError")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "retry" }));
    expect(await screen.findByText("partialData")).toBeInTheDocument();
  });
  it("exposes compact chips: quick preset toggles, applied chips remove, and the Filters drawer applies/closes", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    const user = userEvent.setup();

    // Filters toggle starts collapsed with no applied groups.
    const filtersToggle = screen.getByRole("button", {
      name: /^filtersButton/,
    });
    expect(filtersToggle).toHaveAttribute("aria-haspopup", "dialog");
    expect(filtersToggle).toHaveAttribute("aria-expanded", "false");

    // Quick preset chip applies immediately through the URL lifecycle.
    await user.click(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    );
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?quick_filter=last_day",
      { scroll: false },
    );

    // Applied chips appear with values and per-group remove actions.
    navigation.search =
      "price_min=80000000&rooms=2&district=wola&quick_filter=last_day";
    for (const listener of navigation.listeners) listener();
    expect(await screen.findByText(/PLN 800,000/)).toBeInTheDocument();
    expect(filtersToggle).toHaveTextContent("4");
    await user.click(
      screen.getByRole("button", { name: "chipRemove:priceLabel" }),
    );
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?rooms=2&district=wola&quick_filter=last_day",
      { scroll: false },
    );

    // The drawer opens from the rail, applies a valid draft, and closes.
    await user.click(screen.getByRole("button", { name: "moreFilters" }));
    expect(filtersToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
    fireEvent.change(screen.getByRole("spinbutton", { name: "minimumPrice" }), {
      target: { value: "900000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "applyFilters" }));
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?price_min=90000000&rooms=2&district=wola&quick_filter=last_day",
      { scroll: false },
    );
    expect(filtersToggle).toHaveAttribute("aria-expanded", "false");
  });

  it("filters from the prior browser visit and records the current visit", async () => {
    const priorVisit = "2026-08-26T08:30:00.000Z";
    window.localStorage.setItem(lastVisitStorageKeys.last, priorVisit);
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "quickFilter.since_last_visit" }),
    );

    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?published_from=2026-08-26T08%3A30%3A00.000Z",
      { scroll: false },
    );
    expect(window.localStorage.getItem(lastVisitStorageKeys.last)).not.toBe(
      priorVisit,
    );
    expect(window.sessionStorage.getItem(lastVisitStorageKeys.previous)).toBe(
      priorVisit,
    );
  });

  it("uses the authenticated account visit as the cross-device baseline", async () => {
    const localPriorVisit = "2026-08-26T08:30:00.000Z";
    const accountPriorVisit = "2026-08-25T07:15:00.000Z";
    window.localStorage.setItem(lastVisitStorageKeys.last, localPriorVisit);
    vi.mocked(authApi.fetchCurrentAccount).mockResolvedValue({
      state: "ready",
      data: {
        id: "00000000-0000-4000-8000-000000000001",
        username: "warsaw",
        role: "user",
        must_change_password: false,
        created_at: "2026-01-01T00:00:00Z",
        last_login_at: null,
      },
    });
    vi.mocked(viewHistoryApi.startAccountVisit).mockResolvedValue({
      state: "ready",
      data: {
        visit_id: "30000000-0000-4000-8000-000000000001",
        current_visit_at: "2026-08-29T08:00:00Z",
        previous_visit_at: accountPriorVisit,
      },
    });
    renderExplorer();
    await waitFor(() => {
      expect(viewHistoryApi.startAccountVisit).toHaveBeenCalledWith(
        expect.any(String),
        { signal: expect.any(AbortSignal) },
      );
      expect(
        screen.getByRole("button", {
          name: "quickFilter.since_last_visit",
        }),
      ).toBeEnabled();
    });

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "quickFilter.since_last_visit" }),
    );

    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?published_from=2026-08-25T07%3A15%3A00.000Z",
      { scroll: false },
    );
  });

  it("keeps exactly one attribution surface rendered by the map control", async () => {
    renderExplorer();
    await screen.findByTestId("map");
    expect(document.querySelector(".map-attribution")).toBeNull();
  });
  it("loads more listing pages through the cursor without per-location requests", async () => {
    const user = userEvent.setup();
    const secondPage: catalogApi.ViewportListingPage = {
      items: [
        {
          ...listingPage.items[0]!,
          id: "20000000-0000-4000-8000-000000000010",
          location: {
            ...listingPage.items[0]!.location,
            id: "10000000-0000-4000-8000-000000000002",
            display_name: "Synthetic Wola Gardens",
          },
        },
      ],
      matching_count: 2,
      next_cursor: null,
    };
    vi.mocked(catalogApi.fetchViewportListings).mockImplementation(
      async (query = { bbox: catalogApi.DEFAULT_BBOX }) => {
        if ((query as { cursor?: string }).cursor === "cursor-2") {
          return { state: "ready", data: secondPage };
        }
        return {
          state: "ready",
          data: { ...listingPage, matching_count: 2, next_cursor: "cursor-2" },
        };
      },
    );
    renderExplorer();

    expect(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /Synthetic Wola Gardens/ }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "loadMore" }));

    expect(
      await screen.findByRole("button", { name: /Synthetic Wola Gardens/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Synthetic Central Residence/ }),
    ).toBeInTheDocument();
    expect(catalogApi.fetchViewportListings).toHaveBeenLastCalledWith(
      expect.objectContaining({ cursor: "cursor-2", limit: 20 }),
      { signal: expect.any(AbortSignal) },
    );
    expect(
      screen.queryByRole("button", { name: "loadMore" }),
    ).not.toBeInTheDocument();
  });

  it("replaces the rail with the selected location and restores results on back", async () => {
    const user = userEvent.setup();
    renderExplorer();
    const card = await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    await user.click(card);

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "backToResults" })).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /Synthetic Central Residence/ }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "backToResults" }));

    expect(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText("development · primary")).not.toBeInTheDocument();
    // Focus returns to the card that opened the selected view.
    expect(document.activeElement?.textContent ?? "").toMatch(
      /Synthetic Central Residence/,
    );
  });

  it("keeps prior cards and retries after a background listings error", async () => {
    const user = userEvent.setup();
    let failuresLeft = 1;
    vi.mocked(catalogApi.fetchViewportListings).mockImplementation(
      async (query = { bbox: catalogApi.DEFAULT_BBOX }) => {
        if (query.bbox !== catalogApi.DEFAULT_BBOX && failuresLeft > 0) {
          failuresLeft -= 1;
          return { state: "error" };
        }
        return { state: "ready", data: listingPage };
      },
    );
    renderExplorer();

    expect(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "move-map" }));
    await waitFor(() =>
      expect(screen.getByText("listingsError")).toBeVisible(),
    );
    expect(
      screen.getByRole("button", { name: /Synthetic Central Residence/ }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "retry" }));
    await waitFor(() =>
      expect(screen.queryByText("listingsError")).not.toBeInTheDocument(),
    );
  });

  it("announces the settled listing count once", async () => {
    vi.mocked(catalogApi.fetchViewportListings).mockResolvedValue({
      state: "ready",
      data: { ...listingPage, matching_count: 7 },
    });
    renderExplorer();

    await screen.findByText("listingCountAnnouncement:7");
  });
});
