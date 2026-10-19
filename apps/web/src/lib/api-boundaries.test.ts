import { afterEach, describe, expect, it, vi } from "vitest";
import * as auth from "./auth-api";
import * as catalog from "./catalog-api";
import { revealOfferContacts } from "./contacts-api";
import * as history from "./view-history-api";

type Options = {
  fetcher?: (request: Request) => Promise<Response>;
  signal?: AbortSignal;
};
const credentials = { username: "warsaw", password: "longenough123" };
const reads = [
  ["account", (options?: Options) => auth.fetchCurrentAccount(options)],
  [
    "register",
    (options?: Options) => auth.registerAccount(credentials, options),
  ],
  ["login", (options?: Options) => auth.loginAccount(credentials, options)],
  ["facets", (options?: Options) => catalog.fetchFacets(options)],
  ["map", (options?: Options) => catalog.fetchLocationMap(undefined, options)],
  [
    "location offers",
    (options?: Options) =>
      catalog.fetchLocationOffers("location", undefined, options),
  ],
  ["offer", (options?: Options) => catalog.fetchOfferDetail("offer", options)],
  ["presets", (options?: Options) => catalog.fetchQuickFilters(options)],
  [
    "listings",
    (options?: Options) => catalog.fetchViewportListings(undefined, options),
  ],
  [
    "uncertain listings",
    (options?: Options) =>
      catalog.fetchUnmappedListings({ bbox: catalog.DEFAULT_BBOX }, options),
  ],
  ["contacts", (options?: Options) => revealOfferContacts("offer", options)],
  ["visit", (options?: Options) => history.startAccountVisit("visit", options)],
  [
    "viewed offer",
    (options?: Options) => history.markOfferViewed("offer", options),
  ],
  ["viewed offers", (options?: Options) => history.fetchViewedOffers(options)],
] as const;

afterEach(() => vi.unstubAllGlobals());

describe("API response boundaries", () => {
  it.each(reads)(
    "rejects an empty successful %s response",
    async (_name, request) => {
      const fetcher = vi.fn(async () => new Response(null, { status: 204 }));
      expect(await request({ fetcher })).toMatchObject({ state: "error" });
    },
  );

  it.each(reads)("propagates cancellation for %s", async (_name, request) => {
    const controller = new AbortController();
    const fetcher = vi.fn(async (sent: Request) => {
      expect(sent.signal).toBe(controller.signal);
      return new Response(null, { status: 204 });
    });
    await request({ fetcher, signal: controller.signal });
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it.each(reads)(
    "maps %s transport failure to a stable error",
    async (_name, request) => {
      const fetcher = vi.fn(async () => {
        throw new Error("offline");
      });
      expect(await request({ fetcher })).toMatchObject({ state: "error" });
    },
  );

  it.each([null, "unreadable", { detail: false }])(
    "handles an invalid problem body %j",
    async (body) => {
      const fetcher = vi.fn(async () => Response.json(body, { status: 500 }));
      expect(await auth.fetchCurrentAccount({ fetcher })).toEqual({
        state: "error",
        message: undefined,
      });
      expect(await revealOfferContacts("offer", { fetcher })).toEqual({
        state: "error",
        code: "unknown",
        message: undefined,
      });
    },
  );

  it.each([
    ["disable", auth.disableOwnAccount],
    ["delete", auth.deleteOwnAccount],
  ])("handles %s transport failures", async (_name, request) => {
    const fetcher = vi.fn(async () => {
      throw new Error("offline");
    });
    expect(await request({ fetcher })).toEqual({ state: "error" });
  });

  it("uses the default transport for auth mutations", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetcher);
    await auth.logoutAccount();
    await auth.revokeAllSessions();
    await auth.disableOwnAccount();
    await auth.deleteOwnAccount();
    await auth.changePassword({
      current_password: "oldpassword",
      new_password: "newpassword",
    });
    expect(fetcher).toHaveBeenCalledTimes(5);
  });

  it("passes a signal to password changes and uses the default contact transport", async () => {
    const signal = new AbortController().signal;
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.signal).toBe(signal);
      return new Response(null, { status: 204 });
    });
    await auth.changePassword(
      { current_password: "oldpassword", new_password: "newpassword" },
      { fetcher, signal },
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 })),
    );
    expect(await revealOfferContacts("offer")).toMatchObject({
      state: "error",
    });
  });

  it.each([{ coordinates: [] }, { coordinates: [21] }])(
    "rejects incomplete listing coordinates $coordinates",
    async ({ coordinates }) => {
      const fetcher = vi.fn(async () =>
        Response.json({
          items: [{ location: { geometry: { type: "Point", coordinates } } }],
        }),
      );
      expect(
        await catalog.fetchViewportListings(undefined, { fetcher }),
      ).toEqual({ state: "error" });
    },
  );
});
