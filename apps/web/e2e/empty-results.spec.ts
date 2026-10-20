import { expect, test } from "@playwright/test";

import { installSyntheticCatalog } from "./helpers/catalog-mocks";

for (const width of [320, 390, 1280]) {
  test(`clears stale results and spaces empty actions at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    await installSyntheticCatalog(page);
    await page.route("**/api/v1/listings?**", async (route) => {
      if (!new URL(route.request().url()).searchParams.has("quick_filter")) {
        await route.fallback();
        return;
      }
      await route.fulfill({
        json: { items: [], matching_count: 0, next_cursor: null },
      });
    });
    await page.route("**/api/v1/map/locations?**", async (route) => {
      if (!new URL(route.request().url()).searchParams.has("quick_filter")) {
        await route.fallback();
        return;
      }
      await route.fulfill({
        json: {
          type: "FeatureCollection",
          features: [],
          meta: {
            request_id: "empty",
            feature_count: 0,
            matching_offer_count: 0,
          },
        },
      });
    });
    await page.goto("/?bbox=20.6505%2C51.976733%2C21.4495%2C52.6");
    if (width < 768)
      await page.getByRole("button", { name: /^Show \d+ listings?$/ }).click();
    const cards = page.getByRole("list", {
      name: "Warsaw listings",
      exact: true,
    });
    await expect(cards).toBeVisible();
    await page
      .getByRole("button", { name: "Last 24 hours", exact: true })
      .click();
    const message = page.getByText("No results in this map area", {
      exact: true,
    });
    await expect(message).toBeVisible();
    await expect(cards).toHaveCount(0);
    await expect(page).toHaveURL(/quick_filter=last_day/);
    const clear = page.getByRole("button", { name: "Clear", exact: true });
    const reset = page.getByRole("button", { name: "Reset map", exact: true });
    const [messageBox, clearBox, resetBox] = await Promise.all(
      [message, clear, reset].map((item) => item.boundingBox()),
    );
    expect(
      clearBox!.y - (messageBox!.y + messageBox!.height),
    ).toBeGreaterThanOrEqual(8);
    for (const box of [clearBox!, resetBox!]) {
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
    }
    const controlsSeparated =
      resetBox!.x - (clearBox!.x + clearBox!.width) >= 8 ||
      resetBox!.y - (clearBox!.y + clearBox!.height) >= 8;
    expect(controlsSeparated).toBe(true);
    const nearby = await page
      .getByText("Location uncertain — outside map results", { exact: true })
      .boundingBox();
    expect(
      nearby!.y -
        Math.max(
          clearBox!.y + clearBox!.height,
          resetBox!.y + resetBox!.height,
        ),
    ).toBeGreaterThanOrEqual(12);
    await clear.click();
    await expect(cards).toBeVisible();
    await expect(page).not.toHaveURL(/quick_filter=/);
    await page
      .getByRole("button", { name: "Last 24 hours", exact: true })
      .click();
    await expect(message).toBeVisible();
    await reset.click();
    await expect(page).toHaveURL(/quick_filter=last_day/);
  });

  test(`bounds dates by the latest catalog offer at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    await installSyntheticCatalog(page);
    await page.goto("/");
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    const from = page.getByLabel("Published from", { exact: true });
    const to = page.getByLabel("Published to", { exact: true });
    for (const input of [from, to]) {
      await expect(input).toHaveAttribute("min", "2026-08-01");
      await expect(input).toHaveAttribute("max", "2026-08-01");
      await input.fill("2026-08-02");
      expect(
        await input.evaluate(
          (field: HTMLInputElement) => field.validity.rangeOverflow,
        ),
      ).toBe(true);
      await input.fill("2026-08-01");
    }
    expect(
      await from.evaluate((input: HTMLInputElement) => input.validity.valid),
    ).toBe(true);
    expect(
      await to.evaluate((input: HTMLInputElement) => input.validity.valid),
    ).toBe(true);
    await page.getByRole("button", { name: "Apply", exact: true }).click();
    await expect(page).toHaveURL(/published_from=2026-08-01/);
    await expect(page).toHaveURL(/published_to=2026-08-01/);
  });
}
