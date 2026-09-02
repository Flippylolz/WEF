import { expect, test, type Page } from "@playwright/test";

import { installSyntheticCatalog } from "./helpers/catalog-mocks";

function boxesOverlap(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number },
): boolean {
  return (
    a.x < b.x + b.width &&
    b.x < a.x + a.width &&
    a.y < b.y + b.height &&
    b.y < a.y + a.height
  );
}

async function mapAttributionRendered(page: Page): Promise<boolean> {
  // CI runners cannot create a WebGL context, so MapLibre never mounts and
  // the app correctly falls back to the map-error state. Only environments
  // that actually render the map can assert attribution geometry.
  return page
    .locator(".maplibregl-ctrl-attrib")
    .waitFor({ state: "visible", timeout: 15_000 })
    .then(() => true)
    .catch(() => false);
}

async function assertBadgeClearsAttribution(page: Page) {
  await page.goto("/");
  const rendered = await mapAttributionRendered(page);
  test.skip(
    !rendered,
    "map rendering (WebGL) is unavailable in this environment",
  );

  const attribution = page.locator(".maplibregl-ctrl-attrib");
  const badge = page.locator(".version-badge");
  await expect(attribution).toBeVisible();
  await expect(badge).toBeVisible();
  const attributionBox = await attribution.boundingBox();
  const badgeBox = await badge.boundingBox();
  expect(attributionBox).not.toBeNull();
  expect(badgeBox).not.toBeNull();
  expect(
    boxesOverlap(attributionBox!, badgeBox!),
    "version badge must not cover the map attribution",
  ).toBe(false);
}

test("version badge does not cover the map attribution on desktop", async ({
  page,
}) => {
  await installSyntheticCatalog(page);
  await assertBadgeClearsAttribution(page);
});

test("version badge does not cover the map attribution on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSyntheticCatalog(page);
  await assertBadgeClearsAttribution(page);
});
