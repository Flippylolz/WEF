import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MapExplorer } from "@/components/map-explorer";
import * as catalogApi from "@/lib/catalog-api";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { count?: number }) =>
    values?.count === undefined ? key : `${key}:${values.count}`,
}));

vi.mock("next/dynamic", () => ({
  default: () =>
    function FakeMap({ onFailure }: { onFailure: () => void }) {
      return (
        <div data-testid="map">
          <button type="button" onClick={onFailure}>
            fail-map
          </button>
        </div>
      );
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
  });

  beforeEach(() => {
    vi.spyOn(catalogApi, "fetchLocationMap").mockResolvedValue({
      state: "ready",
      data: mapData,
    });
    vi.spyOn(catalogApi, "fetchFacets").mockResolvedValue({
      state: "ready",
      data: facets,
    });
    vi.spyOn(catalogApi, "fetchLocationOffers").mockResolvedValue({
      state: "ready",
      data: offerPage,
    });
  });

  it("keeps an accessible list and opens backend offer summaries", async () => {
    const user = userEvent.setup();
    render(<MapExplorer />);

    const location = await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    expect(screen.getByText("lowConfidence")).toBeInTheDocument();

    await user.click(location);

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getByText("apartmentPrice")).toBeInTheDocument();
    expect(screen.getByText("parkingPrice")).toBeInTheDocument();
    expect(screen.getByText("storagePrice")).toBeInTheDocument();
    expect(screen.getByText("includedInApartmentPrice")).toBeInTheDocument();
    expect(catalogApi.fetchLocationOffers).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
  });

  it("falls back to the semantic list when the map fails", async () => {
    const user = userEvent.setup();
    render(<MapExplorer />);
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
    render(<MapExplorer />);

    expect(screen.getByText("loading")).toHaveAttribute("role", "status");
    expect(await screen.findByText("error")).toHaveAttribute("role", "alert");
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
    render(<MapExplorer />);

    expect(await screen.findByText("empty")).toHaveAttribute("role", "status");
  });
});
