// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchEstates } from "./estates-api";

describe("fetchEstates", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("requests the typed endpoint from the configured server", async () => {
    vi.stubEnv("WEF_API_URL", "http://api.example.test");
    const fetchMock = vi
      .fn<(request: Request) => Promise<Response>>()
      .mockResolvedValue(
        Response.json({
          items: [
            {
              id: 7,
              title: "Contract House",
              location: { latitude: 40.7128, longitude: -74.006 },
              availability: "available",
              availability_label_key: "estates.availability.available",
            },
          ],
        }),
      );

    const result = await fetchEstates(fetchMock);

    const request = fetchMock.mock.calls[0]?.[0];
    expect(request).toBeInstanceOf(Request);
    expect(request?.url).toBe("http://api.example.test/api/v1/estates");
    expect(request?.method).toBe("GET");
    expect(result).toEqual({
      state: "ready",
      items: [
        {
          id: 7,
          title: "Contract House",
          location: { latitude: 40.7128, longitude: -74.006 },
          availability: "available",
          availability_label_key: "estates.availability.available",
        },
      ],
    });
  });

  it("returns an error state for an API error response", async () => {
    const fetchMock = vi
      .fn<(request: Request) => Promise<Response>>()
      .mockResolvedValue(
        Response.json({ detail: "unavailable" }, { status: 503 }),
      );

    await expect(fetchEstates(fetchMock)).resolves.toEqual({ state: "error" });
  });
});
