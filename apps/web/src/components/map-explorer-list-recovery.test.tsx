import {
  listingPage,
  mapMountCount,
  openFiltersDrawer,
  renderExplorer,
  setupMapExplorer,
} from "./map-explorer.test-support";

import { act, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import * as catalogApi from "@/lib/catalog-api";

describe("map-explorer list-recovery", () => {
  setupMapExplorer();

  it("shows pending pagination while preserving the loaded cards", async () => {
    let resolvePage!: (
      result: catalogApi.ApiResult<catalogApi.ViewportListingPage>,
    ) => void;
    const pending = new Promise<
      catalogApi.ApiResult<catalogApi.ViewportListingPage>
    >((resolve) => {
      resolvePage = resolve;
    });
    vi.mocked(catalogApi.fetchViewportListings).mockImplementation(
      async (query) =>
        query?.cursor
          ? pending
          : { state: "ready", data: { ...listingPage, next_cursor: "next" } },
    );
    renderExplorer();
    await screen.findByRole("button", { name: /Synthetic Central Residence/ });
    await userEvent.click(screen.getByRole("button", { name: "loadMore" }));
    expect(screen.getByRole("button", { name: "loadingMore" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /Synthetic Central Residence/ }),
    ).toBeVisible();
    await act(async () => {
      resolvePage({
        state: "ready",
        data: { items: [], matching_count: 1, next_cursor: null },
      });
    });
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "loadingMore" }),
      ).not.toBeInTheDocument(),
    );
  });

  it("keeps the catalog usable when facets and quick presets fail", async () => {
    vi.mocked(catalogApi.fetchFacets).mockResolvedValue({ state: "error" });
    vi.mocked(catalogApi.fetchQuickFilters).mockResolvedValue({
      state: "error",
    });
    renderExplorer();
    await screen.findByRole("button", { name: /Synthetic Central Residence/ });
    await openFiltersDrawer(userEvent.setup());
    expect(await screen.findByText("facetsError")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "quickFilter.last_day" }),
    ).not.toBeInTheDocument();
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

  it("clears previous cards and counts when Last 24 hours returns no listings", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.fetchViewportListings).mockImplementation(
      async (query = { bbox: catalogApi.DEFAULT_BBOX }) => ({
        state: "ready",
        data: query.quick_filter
          ? { items: [], matching_count: 0, next_cursor: null }
          : listingPage,
      }),
    );
    renderExplorer();
    await screen.findByRole("button", { name: /Synthetic Central Residence/ });

    await user.click(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    );

    await screen.findByText("listingsEmpty");
    expect(
      screen.queryByRole("button", { name: /Synthetic Central Residence/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("listingCount:0")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "clearFilters" }));
    expect(
      await screen.findByRole("button", {
        name: /Synthetic Central Residence/,
      }),
    ).toBeVisible();
  });

  it("does not resurrect cards after an empty success followed by a refresh failure", async () => {
    const user = userEvent.setup();
    let filteredRequests = 0;
    vi.mocked(catalogApi.fetchViewportListings).mockImplementation(
      async (query = { bbox: catalogApi.DEFAULT_BBOX }) => {
        if (!query.quick_filter) return { state: "ready", data: listingPage };
        filteredRequests += 1;
        return filteredRequests === 1
          ? {
              state: "ready",
              data: { items: [], matching_count: 0, next_cursor: null },
            }
          : { state: "error" };
      },
    );
    renderExplorer();
    await screen.findByRole("button", { name: /Synthetic Central Residence/ });
    await user.click(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    );
    await screen.findByText("listingsEmpty");
    await user.click(screen.getByRole("button", { name: "move-map" }));
    await screen.findByText("listingsError");
    expect(
      screen.queryByRole("button", { name: /Synthetic Central Residence/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("listingCount:0")).toBeVisible();
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
