import { execFileSync } from "node:child_process";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const centerOffer = "20000000-0000-4000-8000-000000000001";
const centerLocation = "10000000-0000-4000-8000-000000000001";
const centered = "/?bbox=21.008,52.226,21.0164,52.2334";
const runtimeErrors = new WeakMap<Page, string[]>();
const syntheticContact = "+12025550123";

async function audit(page: Page) {
  // Hydration can replace server-rendered metadata after toHaveTitle passes.
  // Poll the complete audit so persistent violations still fail the journey.
  await expect(async () => {
    await expect(page).toHaveTitle(/\S/);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    await page.bringToFront();
    expect(
      result.violations.map(({ id, impact, nodes }) => ({
        id,
        impact,
        targets: nodes.map(({ target }) => target),
      })),
    ).toEqual([]);
  }).toPass({ timeout: 15_000, intervals: [250, 500, 1000] });
}

async function showList(page: Page, isMobile: boolean) {
  if (isMobile)
    await page.getByRole("button", { name: /Show.*listing/i }).click();
  await expect(
    page.getByRole("button", { name: /Synthetic Central Residence/i }).first(),
  ).toBeVisible();
}

async function openDetail(page: Page, isMobile: boolean) {
  await showList(page, isMobile);
  await page
    .getByRole("button", { name: /Synthetic Central Residence/i })
    .first()
    .click();
  await page
    .getByRole("button", {
      name: "View offer details for Development post · Primary market",
    })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Development post · Primary market" }),
  ).toBeVisible();
}

// Raw traces/video are disabled for private journeys. Failure screenshots are
// explicitly masked before capture; the runner scans artifacts before upload.
test.beforeEach(async ({ context, page }, info) => {
  const errors: string[] = [];
  runtimeErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(error.name));
  if (!/register,|forced-password/.test(info.title)) {
    await context.tracing.start({
      screenshots: true,
      snapshots: true,
      sources: false,
    });
  }
});

test.afterEach(async ({ page }, info) => {
  if (!/register,|forced-password/.test(info.title)) {
    await page.context().tracing.stop({
      path:
        info.status !== info.expectedStatus
          ? info.outputPath("trace.zip")
          : undefined,
    });
  }
  if (
    info.status === info.expectedStatus &&
    (runtimeErrors.get(page)?.length ?? 0) === 0
  )
    return;
  if (page.isClosed()) return;
  await page.screenshot({
    path: info.outputPath("masked-failure.png"),
    mask: [
      page.locator("input"),
      page.locator(".offer-detail-contact-list"),
      page.locator(".account-summary"),
    ],
    animations: "disabled",
  });
  expect(runtimeErrors.get(page)).toEqual([]);
});

test("real routing, migrations, catalog, release identity and shareable filters", async ({
  page,
  request,
  isMobile,
}) => {
  const ready = await request.get("/api/v1/health/ready");
  expect(ready.ok()).toBe(true);
  const map = await request.get(`/api/v1/map/locations${centered.slice(1)}`);
  expect(map.ok()).toBe(true);
  expect(
    (await map.json()).features.some(
      (feature: { id: string }) => feature.id === centerLocation,
    ),
  ).toBe(true);
  await page.goto("/");
  await showList(page, isMobile);
  await audit(page);
  await page.getByRole("button", { name: /^Filters/ }).click();
  await expect(page.getByRole("dialog", { name: "Filters" })).toBeVisible();
  await audit(page);
  await page.getByLabel("Minimum price").fill("900000");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect
    .poll(() => new URL(page.url()).searchParams.get("price_min"))
    .toBe("90000000");
  const url = page.url();
  await page.reload();
  await expect.poll(() => page.url()).toBe(url);
  await expect(page.locator(".version-badge")).toContainText(
    process.env.WEF_E2E_RELEASE!.slice(0, 7),
  );
});

test("real detail, media gallery and keyboard return focus", async ({
  page,
  isMobile,
}) => {
  await page.goto(centered);
  await openDetail(page, isMobile);
  await audit(page);
  const images = page.locator(".offer-media-grid img");
  await expect(images.first()).toBeVisible();
  await expect
    .poll(() =>
      images.first().evaluate((img) => (img as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(0);
  await images.first().click();
  const gallery = page.getByRole("dialog", { name: "Offer media viewer" });
  await expect(
    gallery.getByRole("button", { name: "Close offer detail", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(gallery.getByText("2 of 2", { exact: true })).toBeVisible();
  await page.keyboard.press("ArrowLeft");
  await expect(gallery.getByText("1 of 2", { exact: true })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    gallery.getByRole("button", { name: "Next", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    gallery.getByRole("button", { name: "Close offer detail", exact: true }),
  ).toBeFocused();
  await audit(page);
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Close offer detail", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "View offer details for Development post · Primary market",
    }),
  ).toBeFocused();
});

test("WebGL Chromium initializes and selects an actual database pin", async ({
  page,
}, info) => {
  test.skip(
    info.project.name !== "chromium",
    "Required WebGL smoke is owned by desktop Chromium",
  );
  await page.goto(centered);
  const canvas = page.locator(".maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await expect(page.locator(".map-loading")).toHaveCount(0);
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  await canvas.click({ position: { x: box!.width / 2, y: box!.height / 2 } });
  await expect(
    page.getByRole("heading", { name: "Synthetic Central Residence" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back to results" }).click();
  await expect(
    page.getByRole("button", { name: /Synthetic Central Residence/i }).first(),
  ).toBeVisible();
});

test("no-WebGL fallback retains usable real listings and retry", async ({
  page,
  isMobile,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (...args) {
      if (String(args[0]).includes("webgl")) return null;
      return Reflect.apply(original, this, args);
    } as typeof original;
  });
  await page.goto(centered);
  await expect(
    page.getByText("Use the location list to continue browsing."),
  ).toBeVisible({ timeout: 25_000 });
  await showList(page, isMobile);
  await audit(page);
  if (isMobile)
    await page.getByRole("button", { name: "Show map", exact: true }).click();
  await page.getByRole("button", { name: "Retry map", exact: true }).click();
  await showList(page, isMobile);
  await expect(
    page.getByRole("button", { name: /Synthetic Central Residence/i }).first(),
  ).toBeVisible();
});

test("API failure preserves listings and recovers through the real backend", async ({
  page,
  isMobile,
}) => {
  const project = process.env.WEF_E2E_PROJECT;
  if (!project || !/^wef-e2e-[a-f0-9]{8,12}$/.test(project))
    throw new Error("Missing disposable project identity");
  const apiContainer = `${project}-api-1`;
  await page.goto(centered);
  await showList(page, isMobile);
  execFileSync("docker", ["stop", apiContainer], {
    stdio: "ignore",
    timeout: 30_000,
  });
  try {
    await page.getByRole("button", { name: /^Filters/ }).click();
    await page.getByLabel("Minimum price").fill("700000");
    await page.getByRole("button", { name: "Apply", exact: true }).click();
    await expect(page.getByRole("alert").first()).toBeVisible();
    await expect(
      page
        .getByRole("button", { name: /Synthetic Central Residence/i })
        .first(),
    ).toBeVisible();
    await audit(page);
  } finally {
    execFileSync("docker", ["start", apiContainer], {
      stdio: "ignore",
      timeout: 30_000,
    });
  }
  await expect
    .poll(async () => (await page.request.get("/api/v1/health/ready")).status())
    .toBe(200);
  await page
    .getByRole("button", { name: "Try again", exact: true })
    .first()
    .click();
  await expect(
    page.getByText("Listings are unavailable right now."),
  ).toHaveCount(0);
});

test("register, persistent favorites, private reveal, password change and logout", async ({
  page,
  context,
  isMobile,
}, info) => {
  const password = process.env.WEF_E2E_PASSWORD!;
  const username = `e2e_${info.project.name}_${Date.now().toString(36)}`;
  await page.goto(centered);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByLabel(/^Username/).fill(username);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Confirm password", { exact: true }).fill(password);
  await audit(page);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .last()
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const session = (await context.cookies()).find(
    (cookie) => cookie.name === "wef_session",
  );
  expect(Boolean(session?.httpOnly)).toBe(true);
  expect(session?.sameSite).toBe("Lax");
  await showList(page, isMobile);
  const saved = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      new URL(response.url()).pathname ===
        `/api/v1/favorites/${centerLocation}`,
  );
  await page
    .getByRole("button", { name: "Star this location" })
    .first()
    .click();
  expect((await saved).status()).toBe(204);
  await page.reload();
  await showList(page, isMobile);
  await expect(
    page
      .getByRole("button", { name: "Remove this location from favorites" })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open starred locations", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Starred locations" }),
  ).toBeVisible();
  await audit(page);
  await page
    .getByRole("button", { name: "Close favorites", exact: true })
    .click();
  await openDetail(page, false);
  expect(await page.locator("body").innerText()).not.toContain(
    syntheticContact,
  );
  await page
    .getByRole("button", { name: "Reveal contact", exact: true })
    .click();
  await expect
    .poll(async () =>
      (await page.locator(".offer-detail-contact-list").innerText()).includes(
        syntheticContact,
      ),
    )
    .toBe(true);
  await audit(page);
  await page
    .getByRole("button", { name: "Close offer detail", exact: true })
    .click();
  await page.getByRole("button", { name: username, exact: true }).click();
  await page
    .getByRole("button", { name: "Change password", exact: true })
    .click();
  await page.getByLabel("Current password", { exact: true }).fill(password);
  await page.getByLabel(/^New password/).fill(`${password}-changed`);
  await page
    .getByLabel("Confirm new password", { exact: true })
    .fill(`${password}-changed`);
  await page
    .getByRole("button", { name: "Change password", exact: true })
    .click();
  await expect
    .poll(async () =>
      (await context.cookies()).some((cookie) => cookie.name === "wef_session"),
    )
    .toBe(false);
  await page.getByLabel(/^Username/).fill(username);
  await page.getByLabel(/^Password/).fill(`${password}-changed`);
  await page
    .getByRole("button", { name: "Sign in", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: username, exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect
    .poll(async () =>
      (await context.cookies()).some((cookie) => cookie.name === "wef_session"),
    )
    .toBe(false);
});

test("forced-password account cannot reveal and cross-origin mutations are refused", async ({
  page,
  request,
}, info) => {
  const response = await request.post("/api/v1/auth/login", {
    headers: { Origin: "https://untrusted.invalid" },
    data: { username: "nobody", password: "synthetic-password" },
  });
  expect(response.status()).toBe(403);
  await page.goto(centered);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel(/^Username/).fill(`e2e_forced_${info.project.name}`);
  await page.getByLabel(/^Password/).fill(process.env.WEF_E2E_PASSWORD!);
  await page
    .getByRole("button", { name: "Sign in", exact: true })
    .last()
    .click();
  await expect(
    page.getByText(
      "You must set a new password before using restricted actions.",
    ),
  ).toBeVisible();
  const reveal = await page.request.post(
    `/api/v1/offers/${centerOffer}/contacts/reveal`,
    { data: {} },
  );
  expect(reveal.status()).toBe(403);
  await audit(page);
});

async function tabTo(
  page: Page,
  target: ReturnType<Page["getByRole"]>,
  reverse = false,
) {
  for (let index = 0; index < 80; index += 1) {
    if (await target.evaluate((element) => element === document.activeElement))
      return;
    const macWebKit =
      process.platform === "darwin" &&
      /webkit|safari/.test(test.info().project.name);
    await page.keyboard.press(
      `${macWebKit ? "Alt+" : ""}${reverse ? "Shift+" : ""}Tab`,
    );
  }
  throw new Error(
    `Control was not reachable through keyboard traversal: ${target}`,
  );
}

test("keyboard-only filters, selection, drawer and return focus", async ({
  page,
  isMobile,
}) => {
  await page.goto(centered);
  const filters = page.getByRole("button", { name: /^Filters/ });
  await tabTo(page, filters);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Filters" })).toBeVisible();
  await tabTo(page, page.getByLabel("Minimum price"));
  await expect(page.getByLabel("Minimum price")).toBeFocused();
  await page.keyboard.type("700000");
  await tabTo(
    page,
    page.getByRole("button", { name: "Apply", exact: true }),
    true,
  );
  await page.keyboard.press("Enter");
  await expect
    .poll(() => new URL(page.url()).searchParams.get("price_min"))
    .toBe("70000000");
  if (isMobile) {
    await tabTo(page, page.getByRole("button", { name: /Show.*listing/i }));
    await page.keyboard.press("Enter");
  }
  const listing = page
    .getByRole("button", { name: /Synthetic Central Residence/i })
    .first();
  await tabTo(page, listing);
  await page.keyboard.press("Enter");
  const offer = page.getByRole("button", {
    name: "View offer details for Development post · Primary market",
  });
  await tabTo(page, offer);
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Close offer detail", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(offer).toBeFocused();
});

for (const forceFallback of [false, true]) {
  test(`E28 accepted districts map as areas while quarantined coordinates remain discoverable${forceFallback ? " with no WebGL" : ""}`, async ({
    page,
    request,
    isMobile,
  }) => {
    const map = await request.get(
      "/api/v1/map/locations?bbox=20.8,52.1,21.3,52.4",
    );
    const mapped = (await map.json()).features as {
      id: string;
      properties: {
        coordinate_precision: string;
        location_accuracy: { precision: string; label: string };
      };
    }[];
    expect(
      mapped.some(({ id }) => id === "e2600000-0000-4000-8000-000000000001"),
    ).toBe(true);
    expect(
      mapped.find(({ id }) => id === "e2600000-0000-4000-8000-000000000002")
        ?.properties,
    ).toMatchObject({
      coordinate_precision: "district",
      location_accuracy: { precision: "area", label: "Approximate area" },
    });
    for (const suffix of ["3"]) {
      expect(
        mapped.some(
          ({ id }) => id === `e2600000-0000-4000-8000-00000000000${suffix}`,
        ),
      ).toBe(false);
    }
    const response = await request.get(
      `/api/v1/listings/uncertain${centered.slice(1)}&district=praga-poludnie`,
    );
    expect(response.ok()).toBe(true);
    const discovery = await response.json();
    expect(discovery.matching_count).toBe(1);
    expect(discovery.mapped_matching_count).toBe(0);
    expect(discovery.filter_scope).toBe("non_spatial");
    for (const item of discovery.items)
      expect(item.location).not.toHaveProperty("geometry");
    if (forceFallback) {
      await page.addInitScript(() => {
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function (...args) {
          if (String(args[0]).includes("webgl")) return null;
          return Reflect.apply(original, this, args);
        } as typeof original;
      });
    }
    await page.goto(centered);
    await showList(page, isMobile);
    await expect(page.locator(".map-loading")).toHaveCount(0);
    await expect
      .poll(
        async () =>
          new URL(page.url()).searchParams.get("bbox") !==
            centered.split("bbox=")[1] ||
          (await page
            .getByText("Use the location list to continue browsing.")
            .isVisible()),
      )
      .toBe(true);
    await page.locator(".uncertain-listings summary").click();
    const initialBbox = new URL(page.url()).searchParams.get("bbox");
    for (const [name, label] of [
      ["Synthetic Jugosłowiańska May", "Location unresolved"],
    ]) {
      const trigger = page.getByRole("button", { name: new RegExp(name!) });
      await expect(trigger).toContainText(label!);
      await trigger.focus();
      await page.keyboard.press("Enter");
      const detail = page.getByRole("dialog", {
        name: "Development post · Primary market",
      });
      await expect(detail.locator(".location-accuracy")).toContainText(label!);
      await audit(page);
      await page.keyboard.press("Escape");
      await expect(trigger).toBeFocused();
      expect(new URL(page.url()).searchParams.get("bbox")).toBe(initialBbox);
    }
  });
}

test("E26 WebGL street selection states limited confidence independently of offer completeness", async ({
  page,
}, info) => {
  test.skip(
    info.project.name !== "chromium",
    "Required WebGL regression uses desktop Chromium",
  );
  await page.goto("/?bbox=21.0763269,52.2305096,21.0847269,52.2379096");
  const canvas = page.locator(".maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await expect(page.locator(".map-loading")).toHaveCount(0);
  // Map load and camera URL updates can precede GeoJSON worker rendering.
  await expect(page.getByLabel("Interactive map of Warsaw")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  await canvas.click({ position: { x: box!.width / 2, y: box!.height / 2 } });
  await expect(
    page.getByRole("heading", { name: "Synthetic Ostrzycka" }),
  ).toBeVisible();
  await expect(
    page.getByText("Approximate street location").first(),
  ).toBeVisible();
  await expect(
    page.getByText("Location confidence is limited.").first(),
  ).toBeVisible();
  await audit(page);
  await page
    .getByRole("button", {
      name: "View offer details for Development post · Primary market",
    })
    .click();
  await expect(
    page.getByRole("dialog").locator(".location-accuracy"),
  ).toContainText("Approximate street location");
});

test("E26 WebGL cluster expands without losing precision or finite viewport", async ({
  page,
}, info) => {
  test.skip(
    info.project.name !== "chromium",
    "Required WebGL regression uses desktop Chromium",
  );
  await page.goto(
    "/?bbox=21.0415269,52.1992096,21.1215269,52.2692096&district=praga-poludnie",
  );
  const canvas = page.locator(".maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await expect(page.locator(".map-loading")).toHaveCount(0);
  await expect
    .poll(() => new URL(page.url()).searchParams.get("bbox"))
    .not.toBe("21.0415269,52.1992096,21.1215269,52.2692096");
  // Map load and camera URL updates can precede GeoJSON worker rendering.
  await expect(page.getByLabel("Interactive map of Warsaw")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  const before = new URL(page.url()).searchParams
    .get("bbox")!
    .split(",")
    .map(Number);
  const beforeWidth = before[2]! - before[0]!;
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  await canvas.click({ position: { x: box!.width / 2, y: box!.height / 2 } });
  await expect
    .poll(() => {
      const bounds = new URL(page.url()).searchParams
        .get("bbox")!
        .split(",")
        .map(Number);
      return bounds.every(Number.isFinite) ? bounds[2]! - bounds[0]! : Infinity;
    })
    .toBeLessThan(beforeWidth / 2);
  const after = new URL(page.url()).searchParams
    .get("bbox")!
    .split(",")
    .map(Number);
  expect(after.every(Number.isFinite)).toBe(true);
  expect(after[2]! - after[0]!).toBeLessThan(beforeWidth / 2);
  await expect(
    page.getByRole("button", { name: /Synthetic Ostrzycka/ }),
  ).toContainText("Approximate street location");
  await expect(
    page.getByRole("button", { name: /Synthetic Nearby building/ }),
  ).toContainText("Building location");
});
