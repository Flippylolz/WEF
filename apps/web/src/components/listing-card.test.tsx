import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ListingCard } from "@/components/listing-card";
import type { ViewportListing } from "@/lib/catalog-api";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: { rooms?: string; date?: string }) => {
      if (values?.rooms !== undefined) return `${key}:${values.rooms}`;
      if (values?.date !== undefined) return `${key}:${values.date}`;
      return key;
    },
}));

function listingFixture(
  overrides: Partial<ViewportListing> = {},
): ViewportListing {
  return {
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
      coordinate_precision: "address",
      confidence: "high",
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
    },
    ...overrides,
  } as ViewportListing;
}

function renderCard(overrides: Partial<ViewportListing> = {}) {
  const props = {
    listing: listingFixture(overrides),
    selected: false,
    highlighted: false,
    starred: false,
    showStar: false,
    onSelect: vi.fn(),
    onHighlight: vi.fn(),
    onToggleStar: vi.fn(),
  };
  render(<ListingCard {...props} />);
  return props;
}

describe("ListingCard", () => {
  afterEach(cleanup);

  it("renders the complete summary with price, area, and rooms", () => {
    renderCard();
    expect(screen.getByText("Synthetic Central Residence")).toBeVisible();
    expect(screen.getByText("Synthetic address, Warsaw")).toBeVisible();
    expect(screen.getByText("PLN 800,000–PLN 1,250,000")).toBeVisible();
    expect(screen.getByText("35.00–71.50 m²")).toBeVisible();
    expect(screen.getByText("listingRooms:1–3")).toBeVisible();
    expect(screen.getByText("marketType.primary")).toBeVisible();
    expect(screen.getByText("contentType.development")).toBeVisible();
    expect(screen.getByText("publishedOn:1 Aug 2026")).toBeVisible();
    expect(screen.queryByText("lowConfidence")).not.toBeInTheDocument();
    expect(screen.queryByText("partialData")).not.toBeInTheDocument();
  });

  it("shows the AI-assisted badge when data_origin is ai_assisted", () => {
    renderCard({ data_origin: "ai_assisted" });
    expect(screen.getByText("aiAssistedData")).toBeVisible();
  });

  it("omits missing values instead of inventing them", () => {
    renderCard({
      price_min_minor: null,
      price_max_minor: null,
      area_min_sqm: null,
      area_max_sqm: null,
      rooms_min: null,
      rooms_max: null,
      data_confidence: "partial",
      location: {
        id: "10000000-0000-4000-8000-000000000001",
        display_name: "Sparse Residence",
        display_address: "Sparse address",
        district: null,
        coordinate_precision: "district",
        confidence: "low",
        geometry: { type: "Point", coordinates: [21.0, 52.2] },
      } as ViewportListing["location"],
    });

    expect(screen.queryByText(/PLN/)).not.toBeInTheDocument();
    expect(screen.queryByText(/m²/)).not.toBeInTheDocument();
    expect(screen.queryByText(/listingRooms/)).not.toBeInTheDocument();
    expect(screen.getByText("lowConfidence")).toBeVisible();
    expect(screen.getByText("partialData")).toBeVisible();
  });

  it("selects on click and drives hover highlighting by parent location", async () => {
    const user = userEvent.setup();
    const props = renderCard();

    const card = screen.getByRole("button", {
      name: /Synthetic Central Residence/,
    });
    card.focus();
    expect(props.onHighlight).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    card.blur();
    expect(props.onHighlight).toHaveBeenCalledWith(null);

    await user.click(card);
    expect(props.onSelect).toHaveBeenCalledTimes(1);
    expect(props.onSelect.mock.calls[0]?.[0]?.id).toBe(
      "20000000-0000-4000-8000-000000000001",
    );
  });

  it("marks selection without relying on color and toggles the parent star", async () => {
    const user = userEvent.setup();
    const props = {
      listing: listingFixture(),
      selected: true,
      highlighted: true,
      starred: true,
      showStar: true,
      onSelect: vi.fn(),
      onHighlight: vi.fn(),
      onToggleStar: vi.fn(),
    };
    render(<ListingCard {...props} />);

    const card = screen.getByRole("button", {
      name: /Synthetic Central Residence/,
    });
    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(card.className).toContain("listing-card-highlighted");

    const star = screen.getByRole("button", { name: "unstarLocation" });
    expect(star).toHaveAttribute("aria-pressed", "true");
    await user.click(star);
    expect(props.onToggleStar).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    expect(props.onSelect).not.toHaveBeenCalled();
  });
});
