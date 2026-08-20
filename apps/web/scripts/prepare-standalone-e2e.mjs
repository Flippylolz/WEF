import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const webRoot = join(root, "..");
const standaloneApp = join(webRoot, ".next", "standalone", "apps", "web");
const staticSource = join(webRoot, ".next", "static");
const staticTarget = join(standaloneApp, ".next", "static");
const publicSource = join(webRoot, "public");
const publicTarget = join(standaloneApp, "public");

if (!existsSync(join(standaloneApp, "server.js"))) {
  console.error(
    "Missing standalone server. Run `pnpm --filter web build` before e2e.",
  );
  process.exit(1);
}

mkdirSync(dirname(staticTarget), { recursive: true });
cpSync(staticSource, staticTarget, { recursive: true });
cpSync(publicSource, publicTarget, { recursive: true });
