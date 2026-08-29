import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchViewedOffers,
  markOfferViewed,
  startAccountVisit,
} from "@/lib/view-history-api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("view-history-api", () => {
  it("starts visits and records/list viewed offers", async () => {
    const fetchMock = vi.fn(async (request: Request) => {
      if (request.url.includes("/visits/")) {
        return Response.json({
          visit_id: "30000000-0000-4000-8000-000000000001",
          current_visit_at: "2026-08-29T09:00:00Z",
          previous_visit_at: "2026-08-28T08:00:00Z",
        });
      }
      if (request.method === "PUT") {
        return Response.json({
          offer_id: "20000000-0000-4000-8000-000000000001",
          first_viewed_at: "2026-08-29T09:05:00Z",
          last_viewed_at: "2026-08-29T09:05:00Z",
          view_count: 1,
        });
      }
      return Response.json({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      startAccountVisit("30000000-0000-4000-8000-000000000001"),
    ).resolves.toMatchObject({
      state: "ready",
      data: { previous_visit_at: "2026-08-28T08:00:00Z" },
    });
    await expect(
      markOfferViewed("20000000-0000-4000-8000-000000000001"),
    ).resolves.toMatchObject({ state: "ready", data: { view_count: 1 } });
    await expect(fetchViewedOffers()).resolves.toEqual({
      state: "ready",
      data: { items: [] },
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const visitRequest = fetchMock.mock.calls[0]?.[0] as Request;
    const offerRequest = fetchMock.mock.calls[1]?.[0] as Request;
    expect(visitRequest.method).toBe("PUT");
    expect(visitRequest.headers.get("content-type")).toBe("application/json");
    expect(offerRequest.method).toBe("PUT");
  });

  it("returns stable errors for HTTP and transport failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("nope", { status: 503 })),
    );
    await expect(
      startAccountVisit("30000000-0000-4000-8000-000000000001"),
    ).resolves.toEqual({ state: "error" });
    await expect(
      markOfferViewed("20000000-0000-4000-8000-000000000001"),
    ).resolves.toEqual({ state: "error" });
    await expect(fetchViewedOffers()).resolves.toEqual({ state: "error" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("offline");
      }),
    );
    await expect(fetchViewedOffers()).resolves.toEqual({ state: "error" });
  });
});
