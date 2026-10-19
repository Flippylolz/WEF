import {
  detail,
  renderDrawer,
  setupOfferDetailDrawer,
} from "./offer-detail-drawer.test-support";

import { screen } from "@testing-library/react";

import { describe, expect, it, vi } from "vitest";

import * as catalogApi from "@/lib/catalog-api";

describe("offer-detail-drawer presentation", () => {
  setupOfferDetailDrawer();

  it("renders masked detail fields and verified Telegram link", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer();

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getByText("detailPublicationLabel")).toBeInTheDocument();
    expect(screen.getByText("Masked public text only.")).toBeInTheDocument();
    expect(
      screen.getByText("detailAvailabilityDisclaimer"),
    ).toBeInTheDocument();
    expect(screen.getByText("detailFieldArea")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("href", "https://t.me/elestate_warszawa/42");
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("falls back to raw parser field names and hides duplicate addresses", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: {
        ...detail,
        field_confidence: [
          { field: "area_sqm", confidence: "high" },
          { field: "mystery_field", confidence: "low" },
        ],
        location: {
          ...detail.location,
          display_name: "Synthetic address, Warsaw",
          display_address: "Synthetic address, Warsaw",
        },
      },
    });
    renderDrawer();

    expect(await screen.findByText("detailFieldArea")).toBeInTheDocument();
    expect(screen.getByText("mystery_field")).toBeInTheDocument();
    expect(screen.getAllByText("Synthetic address, Warsaw")).toHaveLength(1);
  });

  it("shows the AI-assisted badge when data_origin is ai_assisted", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: { ...detail, data_origin: "ai_assisted" },
    });
    renderDrawer();

    expect(await screen.findByText("aiAssistedData")).toBeVisible();
  });

  it("shows non-link fallback when verified url is absent", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: { ...detail, verified_source_url: null },
    });
    renderDrawer();

    expect(
      await screen.findByText(/detailSourceFallbackWithId/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "detailOpenTelegram" }),
    ).not.toBeInTheDocument();
  });

  it("renders partial data, omitted prices, and unsafe source urls", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: {
        ...detail,
        data_confidence: "partial",
        price_min_minor: null,
        price_max_minor: null,
        parking_price_min_minor: null,
        parking_price_max_minor: null,
        parking_included_in_price: false,
        storage_included_in_price: false,
        area_min_sqm: null,
        area_max_sqm: null,
        rooms_min: null,
        rooms_max: null,
        verified_source_url: "http://example.test/offer",
      },
    });
    renderDrawer();

    expect(await screen.findByText("partialData")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "detailOpenTelegram" }),
    ).not.toBeInTheDocument();
  });
});
