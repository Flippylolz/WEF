import { expect, test } from "@playwright/test";

import { installSyntheticCatalog } from "./helpers/catalog-mocks";

for (const width of [320, 390, 1280]) {
  test(`keeps the filter header on one row at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await installSyntheticCatalog(page);
    await page.goto("/");
    await page.getByRole("button", { name: "Filters", exact: true }).click();

    const drawer = page.getByRole("dialog", { name: "Filters" });
    const title = drawer.getByRole("heading", { name: "Filters" });
    const clear = drawer.getByRole("button", { name: "Clear", exact: true });
    const apply = drawer.getByRole("button", { name: "Apply", exact: true });
    await expect(title).toBeVisible();
    await expect(clear).toBeVisible();
    await expect(apply).toBeVisible();

    const bounds = await Promise.all(
      [title, clear, apply].map((control) => control.boundingBox()),
    );
    const [headingBox, clearBox, applyBox] = bounds.map((box) => {
      expect(box).not.toBeNull();
      return box!;
    });
    const centerY = (box: typeof headingBox) => box.y + box.height / 2;
    expect(Math.abs(centerY(headingBox) - centerY(clearBox))).toBeLessThan(2);
    expect(Math.abs(centerY(clearBox) - centerY(applyBox))).toBeLessThan(2);
    expect(headingBox.x + headingBox.width).toBeLessThan(clearBox.x);
    expect(clearBox.x + clearBox.width).toBeLessThan(applyBox.x);
    expect(applyBox.x + applyBox.width).toBeLessThanOrEqual(width);
  });
}
