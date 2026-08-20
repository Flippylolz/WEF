import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import tsParser from "@typescript-eslint/parser";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // ESLint 10 removed context.getFilename(); eslint-plugin-react still auto-detects
  // via that API when version is "detect". Pin an explicit React version to skip it.
  // See https://github.com/vercel/next.js/issues/89764
  {
    settings: {
      react: { version: "19.2.8" },
    },
  },
  // eslint-config-next's Babel parser lacks ScopeManager#addGlobals required by
  // ESLint 10. Use typescript-eslint's parser for JS/MJS/CJS/JSX files.
  {
    files: ["**/*.{js,mjs,cjs,jsx}"],
    languageOptions: {
      parser: tsParser,
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
