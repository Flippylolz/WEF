import {
  offerPage,
  renderExplorer,
  setupMapExplorer,
} from "./map-explorer.test-support";

import { screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import * as authApi from "@/lib/auth-api";

import * as catalogApi from "@/lib/catalog-api";

import * as favoritesApi from "@/lib/favorites-api";

import * as viewHistoryApi from "@/lib/view-history-api";

describe("map-explorer selection", () => {
  setupMapExplorer();

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

  it("loads offer detail after explicit offer selection", async () => {
    const user = userEvent.setup();
    const offerDetail: catalogApi.OfferDetail = {
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
          property_type: "unknown",
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
});
