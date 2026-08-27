import { expect, test } from "@playwright/test";

import { installSyntheticCatalog } from "./helpers/catalog-mocks";

test.describe("map explorer critical path", () => {
  test("selects a location, opens offer detail with verified Telegram link", async ({
    page,
  }) => {
    await installSyntheticCatalog(page, "ready");
    await page.goto("/");

    await expect(
      page.getByRole("button", { name: /Synthetic Central Residence/i }),
    ).toBeVisible({ timeout: 30_000 });

    await page
      .getByRole("button", { name: /Synthetic Central Residence/i })
      .click();

    await expect(
      page.getByRole("button", {
        name: "View offer details for development · primary",
      }),
    ).toBeVisible();

    await page
      .getByRole("button", {
        name: "View offer details for development · primary",
      })
      .click();

    await expect(page.getByTestId("offer-detail-overlay")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Open in Telegram" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Open in Telegram" }),
    ).toHaveAttribute("href", "https://t.me/elestate_warszawa/42");
  });

  test("shows missing verified link fallback for offers without a public URL", async ({
    page,
  }) => {
    await installSyntheticCatalog(page, "ready");
    await page.goto("/");

    await page
      .getByRole("button", { name: /Synthetic Central Residence/i })
      .click();
    await page
      .getByRole("button", {
        name: "View offer details for secondary · no verified link",
      })
      .click();

    await expect(page.getByTestId("offer-detail-overlay")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Open in Telegram" }),
    ).toHaveCount(0);
    await expect(
      page.getByText(/No verified public link is available/i),
    ).toBeVisible();
  });

  test("keeps filters messaging when the map API fails", async ({ page }) => {
    await installSyntheticCatalog(page, "map_error");
    await page.goto("/");

    await expect(
      page.getByText("Map data is unavailable right now.").first(),
    ).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Retry map" })).toBeVisible();
  });

  test("keeps the map and panel toggle visible when the sidebar is collapsed", async ({
    page,
  }) => {
    await installSyntheticCatalog(page, "ready");
    await page.goto("/");

    await expect(
      page.getByRole("button", { name: /Synthetic Central Residence/i }),
    ).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Hide panel" }).click();

    // CI intentionally disables MapLibre, so assert the layout-owned map
    // region rather than the optional canvas. The collapsed-grid regression
    // reduced this region to zero width regardless of map availability.
    await expect(page.locator(".map-region")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Show panel" }),
    ).toBeVisible();
  });

  test("does not re-enter map rendering during rapid sidebar resizes", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await installSyntheticCatalog(page, "ready");
    await page.goto("/");

    await expect(
      page.getByRole("button", { name: /Synthetic Central Residence/i }),
    ).toBeVisible({ timeout: 30_000 });

    for (let index = 0; index < 4; index += 1) {
      await page.getByRole("button", { name: "Hide panel" }).click();
      await page.getByRole("button", { name: "Show panel" }).click();
    }
    await page.waitForTimeout(500);

    expect(
      pageErrors.filter((message) =>
        message.includes("Attempting to run(), but is already running"),
      ),
    ).toEqual([]);
  });
});
