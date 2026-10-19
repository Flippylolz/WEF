// @vitest-environment node
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, expect, test, vi } from "vitest";
const io = vi.hoisted(() => ({
  exists: vi.fn(),
  mkdir: vi.fn(),
  copy: vi.fn(),
}));
vi.mock("node:fs", () => ({
  existsSync: io.exists,
  mkdirSync: io.mkdir,
  cpSync: io.copy,
}));
const webRoot = resolve(fileURLToPath(new URL("../../", import.meta.url)));
const standalone = join(webRoot, ".next", "standalone", "apps", "web");

beforeEach(() => {
  vi.resetModules();
  vi.resetAllMocks();
});
test("copies static and public assets into an existing standalone application", async () => {
  io.exists.mockReturnValue(true);
  await import("../../scripts/prepare-standalone-e2e.mjs");
  expect(io.exists).toHaveBeenCalledWith(join(standalone, "server.js"));
  expect(io.mkdir).toHaveBeenCalledWith(join(standalone, ".next"), {
    recursive: true,
  });
  expect(io.copy.mock.calls).toEqual([
    [
      join(webRoot, ".next", "static"),
      join(standalone, ".next", "static"),
      { recursive: true },
    ],
    [join(webRoot, "public"), join(standalone, "public"), { recursive: true }],
  ]);
});
test("missing standalone server refuses preparation before copying assets", async () => {
  io.exists.mockReturnValue(false);
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.spyOn(process, "exit").mockImplementation(() => {
    throw new Error("synthetic exit");
  });
  try {
    await expect(
      import("../../scripts/prepare-standalone-e2e.mjs"),
    ).rejects.toThrow("synthetic exit");
    expect(process.exit).toHaveBeenCalledWith(1);
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining("Missing standalone server"),
    );
    expect(io.copy).not.toHaveBeenCalled();
  } finally {
    vi.restoreAllMocks();
  }
});
