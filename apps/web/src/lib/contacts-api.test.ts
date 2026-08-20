import { describe, expect, it, vi } from "vitest";

import { revealOfferContacts } from "@/lib/contacts-api";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("contacts-api", () => {
  it("reveals contacts with no-store credentials", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.method).toBe("POST");
      expect(request.credentials).toBe("include");
      expect(request.headers.get("Content-Type")).toBe("application/json");
      expect(request.cache).toBe("no-store");
      return jsonResponse(200, {
        contacts: [
          {
            kind: "telegram",
            value: "@seller",
            masked_value: "@s***r",
          },
        ],
      });
    });

    const result = await revealOfferContacts(
      "20000000-0000-4000-8000-000000000001",
      { fetcher },
    );

    expect(result).toEqual({
      state: "ready",
      data: {
        contacts: [
          {
            kind: "telegram",
            value: "@seller",
            masked_value: "@s***r",
          },
        ],
      },
    });
  });

  it("maps reveal status codes to stable error codes", async () => {
    const cases = [
      [401, "unauthorized"],
      [403, "forbidden"],
      [404, "not_found"],
      [429, "rate_limited"],
      [503, "unavailable"],
    ] as const;

    for (const [status, code] of cases) {
      const fetcher = vi.fn(async () =>
        jsonResponse(status, { detail: "blocked" }),
      );
      const result = await revealOfferContacts(
        "20000000-0000-4000-8000-000000000001",
        { fetcher },
      );
      expect(result).toEqual({
        state: "error",
        code,
        message: "blocked",
      });
    }
  });
});
