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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MapExplorer } from "@/components/map-explorer";
import * as authApi from "@/lib/auth-api";
import * as catalogApi from "@/lib/catalog-api";
import * as favoritesApi from "@/lib/favorites-api";

const navigation = vi.hoisted(() => ({
  listeners: new Set<() => void>(),
  pathname: "/",
  push: vi.fn(),
  replace: vi.fn(),
  search: "",
}));

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: { count?: number; room?: number }) => {
      if (values?.count !== undefined) return `${key}:${values.count}`;
      if (values?.room !== undefined) return `${key}:${values.room}`;
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

vi.mock("next/dynamic", () => ({
  default: () =>
    function FakeMap({
      onFailure,
      onSelect,
      onViewportChange,
    }: {
      onFailure: () => void;
      onSelect: (locationId: string) => void;
      onViewportChange: (bbox: string) => void;
    }) {
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

const offerPage: catalogApi.LocationOfferPage = {
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
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "error",
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: { items: [] },
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

    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
    expect(screen.getAllByText("loading").length).toBeGreaterThan(0);
    const errors = await screen.findAllByText("error");
    expect(errors.some((error) => error.getAttribute("role") === "alert")).toBe(
      true,
    );
    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
    expect(screen.queryByTestId("map")).not.toBeInTheDocument();
  });

  it("announces an empty backend projection", async () => {
    vi.mocked(catalogApi.fetchLocationMap).mockResolvedValue({
      state: "ready",
      data: {
        ...mapData,
        features: [],
        meta: { ...mapData.meta, feature_count: 0 },
      },
    });
    renderExplorer();

    expect(await screen.findByText("empty")).toHaveAttribute("role", "status");
    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
  });

  it("restores a combined URL filter query and clears to Warsaw defaults", async () => {
    navigation.search =
      "price_min=80000000&price_max=125000000&area_min=35&area_max=71.5" +
      "&rooms=2&district=wola&market_type=secondary&content_type=unit" +
      "&published_from=2026-08-01T00%3A00%3A00.000Z" +
      "&published_to=2026-08-31T23%3A59%3A59.999Z";
    const user = userEvent.setup();
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

    expect(
      await screen.findByTestId("offer-detail-overlay"),
    ).toBeInTheDocument();
    expect(screen.getByText("Masked public text only.")).toBeInTheDocument();
    expect(catalogApi.fetchOfferDetail).toHaveBeenCalledWith(
      "20000000-0000-4000-8000-000000000001",
      { signal: expect.any(AbortSignal) },
    );
  });
});
