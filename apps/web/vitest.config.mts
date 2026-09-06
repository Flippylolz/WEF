import { coverageConfigDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      exclude: [...coverageConfigDefaults.exclude, "src/**/*.test-support.tsx"],
      reporter: ["json-summary", "text"],
      thresholds: {
        lines: 90,
        branches: 90,
      },
    },
  },
});
