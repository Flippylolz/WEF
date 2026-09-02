import { expect, test } from "@playwright/test";

import { installSyntheticCatalog } from "./helpers/catalog-mocks";

test("enforces a nonce-based script policy without unsafe-inline", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await installSyntheticCatalog(page);
  const response = await page.goto("/");

  const csp = response?.headers()["content-security-policy"] ?? "";
  const scriptDirective = csp
    .split(";")
    .map((directive) => directive.trim())
    .find((directive) => directive.startsWith("script-src"));
  expect(scriptDirective, "script-src directive present").toBeTruthy();
  expect(scriptDirective).toContain("'nonce-");
  expect(scriptDirective).not.toContain("'unsafe-inline'");

  // Next.js stamps its first-party scripts with the app-issued nonce.
  await expect(page.locator("script[nonce]").first()).toBeAttached();

  // Every script (including the MapLibre worker bootstrap path) must run
  // without CSP refusal reports.
  await expect.poll(() => consoleErrors.join("\n")).not.toContain("Refused to");
});
