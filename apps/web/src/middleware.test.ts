/** @vitest-environment node */
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { config, middleware } from "./middleware";

afterEach(() => vi.unstubAllEnvs());

describe("request content security policy", () => {
  it.each(["production", "development"])(
    "issues a matching request/response nonce in %s",
    (environment) => {
      vi.stubEnv("NODE_ENV", environment);
      const response = middleware(
        new NextRequest("https://wef.example.test/", {
          headers: { "x-test-request": "preserved" },
        }),
      );
      const nonce = response.headers.get("x-middleware-request-x-nonce");
      expect(nonce).toBeTruthy();
      expect(atob(nonce!)).toMatch(/^[0-9a-f-]{36}$/);
      const csp = response.headers.get("Content-Security-Policy");
      expect(csp).toContain(`script-src 'nonce-${nonce}' 'strict-dynamic'`);
      expect(
        response.headers.get("x-middleware-request-content-security-policy"),
      ).toBe(csp);
      expect(response.headers.get("x-middleware-request-x-test-request")).toBe(
        "preserved",
      );
      expect(csp).toContain("frame-ancestors 'none'");
      expect(csp).toContain("object-src 'none'");
      expect(csp?.includes("'unsafe-eval'")).toBe(
        environment === "development",
      );
      expect(csp?.includes("ws://localhost:*")).toBe(
        environment === "development",
      );
      expect(config.matcher).toHaveLength(1);
      expect(
        middleware(new NextRequest("https://wef.example.test/")).headers.get(
          "x-middleware-request-x-nonce",
        ),
      ).not.toBe(nonce);
    },
  );
});
