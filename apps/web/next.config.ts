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
