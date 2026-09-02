import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const require = createRequire(import.meta.url);
const packageRoot = dirname(require.resolve("maplibre-gl/package.json"));
const configDirectory = dirname(fileURLToPath(import.meta.url));
const publicDirectory = fileURLToPath(new URL("./public", import.meta.url));
const maplibreDirectory = join(publicDirectory, "vendor", "maplibre");
const monorepoRoot = join(configDirectory, "../..");

mkdirSync(maplibreDirectory, { recursive: true });
for (const asset of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(
    join(packageRoot, "dist", asset),
    join(maplibreDirectory, asset),
  );
}

const nextConfig: NextConfig = {
  output: "standalone",
  // Do not disclose the framework stack on public responses (audit F-8).
  poweredByHeader: false,
  // TypeScript 7 has no stable JS API yet. Keep `typescript` aliased to
  // @typescript/typescript6 for eslint/openapi-typescript/Next API mode, and
  // provide tsc via @typescript/native (typescript@7). Force API mode so Next
  // does not require typescript/bin/tsc from the aliased package.
  experimental: {
    useTypeScriptCli: false,
  },
  // pnpm nests helpers under the monorepo store; Node 22 resolves the ESM
  // export branch that NFT otherwise omits from standalone traces.
  outputFileTracingRoot: monorepoRoot,
  outputFileTracingIncludes: {
    "*": [
      "../../node_modules/.pnpm/@swc+helpers@*/node_modules/@swc/helpers/esm/**/*",
    ],
  },
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
