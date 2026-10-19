import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import * as catalog from "@/lib/catalog-api";
import { useMapCatalog } from "./use-map-catalog";
import { UnmappedListings } from "./unmapped-listings";

vi.mock("next-intl", () => ({ useTranslations: () => (key: string) => key }));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const query = { bbox: catalog.DEFAULT_BBOX };

function cacheWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

it("treats a restored catalog cache without pages as an empty list", () => {
  vi.spyOn(catalog, "fetchFacets").mockResolvedValue({ state: "error" });
  vi.spyOn(catalog, "fetchQuickFilters").mockResolvedValue({ state: "error" });
  vi.spyOn(catalog, "fetchLocationMap").mockResolvedValue({ state: "error" });
  const { client, wrapper } = cacheWrapper();
  client.setQueryData(["viewport-listings", ""], { pages: [], pageParams: [] });
  const prefetch = vi.spyOn(client, "prefetchInfiniteQuery");
  const { result } = renderHook(() => useMapCatalog("", query), { wrapper });
  expect(result.current.listingCount).toBe(0);
  expect(result.current.listings).toEqual([]);
  expect(prefetch).not.toHaveBeenCalled();
});

it("treats a restored uncertain-listing cache without pages as empty", () => {
  const { client, wrapper } = cacheWrapper();
  client.setQueryData(["unmapped-listings", query], {
    pages: [],
    pageParams: [],
  });
  render(
    <UnmappedListings
      query={query}
      onOfferTrigger={vi.fn()}
      onSelectOffer={vi.fn()}
      favoriteIds={new Set()}
      signedIn={false}
      onToggleStar={vi.fn()}
    />,
    { wrapper },
  );
  expect(screen.getByText("uncertainTitle (0)")).toBeInTheDocument();
  expect(screen.getByText("uncertainEmpty")).toBeInTheDocument();
});
