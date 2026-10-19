// @vitest-environment node
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

const state = vi.hoisted(() => ({
  files: {} as Record<string, string>,
  chunks: false,
}));
vi.mock("node:fs", () => ({
  existsSync: (path: string) =>
    path.endsWith("/.next/static/chunks") && state.chunks,
  readdirSync: (path: string) => {
    const prefix = path + "/";
    const children = new Map<string, boolean>();
    for (const file of Object.keys(state.files)) {
      if (!file.startsWith(prefix)) continue;
      const suffix = file.slice(prefix.length);
      const [name] = suffix.split("/");
      children.set(name, suffix.includes("/"));
    }
    return [...children].map(([name, directory]) => ({
      name,
      isDirectory: () => directory,
    }));
  },
  readFileSync: (path: string) => {
    if (!(path in state.files)) throw new Error("synthetic missing file");
    return state.files[path];
  },
}));
const argv = process.argv;
const root = resolve(fileURLToPath(new URL("../../", import.meta.url)));
function source(files: Record<string, string>) {
  state.files = Object.fromEntries(
    Object.entries(files).map(([name, body]) => [`${root}/${name}`, body]),
  );
}
beforeEach(() => {
  vi.resetModules();
  state.files = {};
  state.chunks = false;
  process.argv = ["node", "check-frontend-boundaries.mjs"];
  vi.spyOn(console, "log").mockImplementation(() => {});
});
afterEach(() => {
  process.argv = argv;
  vi.restoreAllMocks();
});
async function check() {
  await import("../../scripts/check-frontend-boundaries.mjs");
}

test("walks aliased, relative, re-exported and dynamic imports without counting test infrastructure", async () => {
  source({
    "src/entry.ts": `import { value } from "@/shared"; export { value } from "./nested"; import("./lazy"); import("external-package"); import("./missing"); import(variable); import(); export { value };`,
    "src/shared.ts": "export const value = 1;",
    "src/nested/index.tsx": `export { value } from "../shared";`,
    "src/lazy.tsx": `import { value } from "@/shared"; export default value;`,
    "src/ignored.test.ts": `import "./ignored.test";`,
    "src/test/fixture.ts": `import "./fixture";`,
    "src/readme.txt": "fixture text",
  });
  await check();
  expect(console.log).toHaveBeenCalledWith(
    "Frontend boundaries: 4 source modules, no import cycles.",
  );
});

test("rejects a source import cycle with its concrete file path", async () => {
  source({ "src/a.ts": `import "./b";`, "src/b.ts": `import "./a";` });
  await expect(check()).rejects.toThrow(
    "Frontend import cycle: src/a.ts -> src/b.ts -> src/a.ts",
  );
});

test("reports an empty source inventory without inventing dependencies", async () => {
  await check();
  expect(console.log).toHaveBeenCalledWith(
    "Frontend boundaries: 0 source modules, no import cycles.",
  );
});

test("bundle checking requires the compiled chunks directory", async () => {
  process.argv.push("--bundle");
  await expect(check()).rejects.toThrow("Production build chunks are missing");
});

test("bundle checking requires at least one JavaScript chunk", async () => {
  process.argv.push("--bundle");
  state.chunks = true;
  source({ ".next/static/chunks/style.css": "body{}" });
  await expect(check()).rejects.toThrow(
    "Production JavaScript chunks are missing",
  );
});

test.each([0, -1, 1.5, "100", null])(
  "bundle budget must be a positive safe integer: %s",
  async (budget) => {
    process.argv.push("--bundle");
    state.chunks = true;
    source({
      ".next/static/chunks/app.js": "var fixture = 1;",
      "frontend-budgets.json": JSON.stringify({ maxGzipBytes: budget }),
    });
    await expect(check()).rejects.toThrow("Invalid frontend bundle budget");
  },
);

test("compressed production bytes must fit within the checked-in budget", async () => {
  process.argv.push("--bundle");
  state.chunks = true;
  source({
    ".next/static/chunks/app.js": "var fixture = 1;",
    "frontend-budgets.json": JSON.stringify({ maxGzipBytes: 1 }),
  });
  await expect(check()).rejects.toThrow("exceed 1");
});

test("a valid bundle reports measured gzip bytes and chunk count", async () => {
  process.argv.push("--bundle");
  state.chunks = true;
  source({
    ".next/static/chunks/app.js": "var fixture = 1;",
    ".next/static/chunks/nested/lazy.js": "var lazy = 2;",
    "frontend-budgets.json": JSON.stringify({ maxGzipBytes: 1000 }),
  });
  await check();
  expect(console.log).toHaveBeenLastCalledWith(
    expect.stringMatching(
      /^Production JavaScript: \d+ gzip bytes across 2 chunks \(budget 1000\)\.$/,
    ),
  );
});
