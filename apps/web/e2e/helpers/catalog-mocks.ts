import type { Page } from "@playwright/test";

import {
  filterFacets,
  locationOffers,
  mapLocations,
  offerDetailMissingLink,
  offerDetailVerified,
  OFFER_ID,
  OFFER_ID_NO_LINK,
  quickFilters,
  viewportListings,
} from "../synthetic-catalog";

export type CatalogMode = "ready" | "map_error";

const EMPTY_MAP_STYLE = {
  version: 8,
  name: "e2e-empty",
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#dfe8e3" },
    },
  ],
};

export async function installSyntheticCatalog(
  page: Page,
  mode: CatalogMode = "ready",
): Promise<void> {
  await page.route("**/tiles.openfreemap.org/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/styles/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(EMPTY_MAP_STYLE),
      });
      return;
    }
    await route.fulfill({ status: 204, body: "" });
  });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path === "/api/v1/auth/me") {
      await route.fulfill({ status: 401, body: "" });
      return;
    }
    if (path === "/api/v1/favorites") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
      return;
    }
    if (path === "/api/v1/filter-facets") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(filterFacets),
      });
      return;
    }
    if (path === "/api/v1/quick-filters") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(quickFilters),
      });
      return;
    }
    if (path === "/api/v1/map/locations") {
      if (mode === "map_error") {
        await route.fulfill({ status: 500, body: "error" });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mapLocations),
      });
      return;
    }
    if (path === `/api/v1/offers/${OFFER_ID}`) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(offerDetailVerified),
      });
      return;
    }
    if (path === `/api/v1/offers/${OFFER_ID_NO_LINK}`) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(offerDetailMissingLink),
      });
      return;
    }
    if (path === "/api/v1/listings") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(viewportListings),
      });
      return;
    }
    if (/^\/api\/v1\/locations\/[^/]+\/offers$/.test(path)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(locationOffers),
      });
      return;
    }

    await route.fulfill({ status: 404, body: "unmocked" });
  });
}
