import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const require = createRequire(import.meta.url);
const packageRoot = dirname(require.resolve("maplibre-gl/package.json"));
const publicDirectory = fileURLToPath(new URL("./public", import.meta.url));
const maplibreDirectory = join(publicDirectory, "vendor", "maplibre");

mkdirSync(maplibreDirectory, { recursive: true });
for (const asset of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(
    join(packageRoot, "dist", asset),
    join(maplibreDirectory, asset),
  );
}

const nextConfig: NextConfig = {
  output: "standalone",
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

export default withNextIntl(nextConfig);
