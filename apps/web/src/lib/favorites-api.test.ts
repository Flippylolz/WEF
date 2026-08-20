import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addFavorite,
  fetchFavorites,
  removeFavorite,
} from "@/lib/favorites-api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("favorites-api", () => {
  it("treats PUT and DELETE 204 as success", async () => {
    const fetchMock = vi.fn(async (request: Request) => {
      if (request.method === "PUT" || request.method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      addFavorite("10000000-0000-4000-8000-000000000001"),
    ).resolves.toEqual({ state: "ready", data: null });
    await expect(
      removeFavorite("10000000-0000-4000-8000-000000000001"),
    ).resolves.toEqual({ state: "ready", data: null });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const first = fetchMock.mock.calls[0]?.[0] as Request;
    const second = fetchMock.mock.calls[1]?.[0] as Request;
    expect(first.url).toContain(
      "/api/v1/favorites/10000000-0000-4000-8000-000000000001",
    );
    expect(first.method).toBe("PUT");
    expect(second.url).toContain(
      "/api/v1/favorites/10000000-0000-4000-8000-000000000001",
    );
    expect(second.method).toBe("DELETE");
  });

  it("lists favorites from JSON payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          items: [
            {
              location_id: "10000000-0000-4000-8000-000000000001",
              display_name: "Synthetic Central Residence",
              display_address: "Synthetic address, Warsaw",
              district: "srodmiescie",
              created_at: "2026-08-20T12:00:00+00:00",
            },
          ],
        }),
      ),
    );

    await expect(fetchFavorites()).resolves.toEqual({
      state: "ready",
      data: {
        items: [
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ],
      },
    });
  });
});
