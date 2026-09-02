import { expect, test } from "@playwright/test";

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

async function assertBadgeClearsAttribution(
  page: import("@playwright/test").Page,
) {
  const attribution = page.locator(".maplibregl-ctrl-attrib");
  const badge = page.locator(".version-badge");
  // Software WebGL on CI runners initializes MapLibre slowly; give the
  // attribution control time to mount before judging visibility.
  await expect(attribution).toBeVisible({ timeout: 30_000 });
  await expect(badge).toBeVisible({ timeout: 30_000 });
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
  await page.goto("/");
  await assertBadgeClearsAttribution(page);
});

test("version badge does not cover the map attribution on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSyntheticCatalog(page);
  await page.goto("/");
  await assertBadgeClearsAttribution(page);
});
