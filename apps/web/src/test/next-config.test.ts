// @vitest-environment node
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, expect, test, vi } from "vitest";

const calls = vi.hoisted(() => ({
  mkdir: vi.fn(),
  copy: vi.fn(),
  resolve: vi.fn(() => "/dependency/maplibre-gl/package.json"),
  intl: vi.fn(() => (configuration: unknown) => configuration),
}));
vi.mock("node:fs", () => ({
  mkdirSync: calls.mkdir,
  copyFileSync: calls.copy,
}));
vi.mock("node:module", () => ({
  createRequire: () => ({ resolve: calls.resolve }),
}));
vi.mock("next-intl/plugin", () => ({ default: calls.intl }));

const webRoot = resolve(fileURLToPath(new URL("../../", import.meta.url)));
const vendor = join(webRoot, "public", "vendor", "maplibre");

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
});

test("build config publishes the pinned worker pair and preserves standalone boundaries", async () => {
  const { default: config } = await import("../../next.config");
  expect(calls.resolve).toHaveBeenCalledWith("maplibre-gl/package.json");
  expect(calls.mkdir).toHaveBeenCalledWith(vendor, { recursive: true });
  expect(calls.copy.mock.calls).toEqual([
    [
      "/dependency/maplibre-gl/dist/maplibre-gl-worker.mjs",
      join(vendor, "maplibre-gl-worker.mjs"),
    ],
    [
      "/dependency/maplibre-gl/dist/maplibre-gl-shared.mjs",
      join(vendor, "maplibre-gl-shared.mjs"),
    ],
  ]);
  expect(config).toMatchObject({
    output: "standalone",
    poweredByHeader: false,
    experimental: { useTypeScriptCli: false },
    outputFileTracingRoot: resolve(webRoot, "../.."),
    outputFileTracingIncludes: {
      "*": [
        "../../node_modules/.pnpm/@swc+helpers@*/node_modules/@swc/helpers/esm/**/*",
      ],
    },
  });
  expect(calls.intl).toHaveBeenCalledWith("./src/i18n/request.ts");
});

test("failure to publish a required worker stops the build configuration", async () => {
  calls.copy.mockImplementationOnce(() => {
    throw new Error("synthetic write refusal");
  });
  await expect(import("../../next.config")).rejects.toThrow(
    "synthetic write refusal",
  );
});
