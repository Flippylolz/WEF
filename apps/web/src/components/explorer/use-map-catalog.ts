"use client";
import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  fetchFacets,
  fetchQuickFilters,
  fetchLocationMap,
  fetchViewportListings,
  type ViewportListing,
} from "@/lib/catalog-api";
import { toMapLocationQuery } from "@/lib/map-search-params";
const LISTING_PAGE_SIZE = 20;

export function useMapCatalog(
  canonicalSearch: string,
  mapQueryParams: ReturnType<typeof toMapLocationQuery>,
) {
  const queryClient = useQueryClient();
  const facetsQuery = useQuery({
    queryKey: ["filter-facets"],
    queryFn: async ({ signal }) => {
      const result = await fetchFacets({ signal });
      if (result.state === "error") throw new Error("facets");
      return result.data;
    },
  });
  const quickFiltersQuery = useQuery({
    queryKey: ["quick-filters"],
    queryFn: async ({ signal }) => {
      const result = await fetchQuickFilters({ signal });
      if (result.state === "error") throw new Error("quick-filters");
      return result.data.items;
    },
  });
  const mapQuery = useQuery({
    queryKey: ["location-map", canonicalSearch],
    queryFn: async ({ signal }) => {
      const result = await fetchLocationMap(mapQueryParams, { signal });
      if (result.state === "error") throw new Error("map");
      return result.data;
    },
    placeholderData: keepPreviousData,
  });
  const listingsQuery = useInfiniteQuery({
    queryKey: ["viewport-listings", canonicalSearch],
    queryFn: async ({ pageParam, signal }) => {
      const result = await fetchViewportListings(
        {
          ...mapQueryParams,
          ...(pageParam ? { cursor: pageParam } : {}),
          limit: LISTING_PAGE_SIZE,
        },
        { signal },
      );
      if (result.state === "error") throw new Error("listings");
      return result.data;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    placeholderData: keepPreviousData,
  });
  const listings = useMemo(
    () => listingsQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [listingsQuery.data],
  );
  const listingCount = listingsQuery.data?.pages[0]?.matching_count ?? 0;
  const listingPagesSettled =
    listingsQuery.isSuccess && !listingsQuery.isFetching;

  // A failed refresh must keep the last safe card collection on screen
  // (placeholderData only covers pending states, not errors). The snapshot
  // adjusts during render from the latest successful page set.
  const [lastGoodListings, setLastGoodListings] = useState<ViewportListing[]>(
    [],
  );
  const [lastGoodListingCount, setLastGoodListingCount] = useState(0);
  if (
    listingsQuery.isSuccess &&
    listings.length > 0 &&
    listings !== lastGoodListings
  ) {
    setLastGoodListings(listings);
    setLastGoodListingCount(listingCount);
  }
  const effectiveListings = listings.length > 0 ? listings : lastGoodListings;
  const effectiveListingCount =
    listingCount > 0 ? listingCount : lastGoodListingCount;
  // Bounded one-page-ahead prefetch keeps Load more instant without ever
  // requesting offers per location.
  useEffect(() => {
    if (!listingPagesSettled) return;
    const nextCursor = listingsQuery.data?.pages.at(-1)?.next_cursor;
    if (nextCursor === undefined || nextCursor === null) return;
    void queryClient.prefetchInfiniteQuery({
      queryKey: ["viewport-listings", canonicalSearch],
      queryFn: async ({ pageParam, signal }) => {
        const result = await fetchViewportListings(
          {
            ...mapQueryParams,
            ...(pageParam ? { cursor: pageParam } : {}),
            limit: LISTING_PAGE_SIZE,
          },
          { signal },
        );
        if (result.state === "error") throw new Error("listings");
        return result.data;
      },
      initialPageParam: undefined as string | undefined,
      getNextPageParam: (lastPage: { next_cursor: string | null }) =>
        lastPage.next_cursor ?? undefined,
      pages: 1,
    });
  }, [
    canonicalSearch,
    listingPagesSettled,
    listingsQuery.data,
    mapQueryParams,
    queryClient,
  ]);

  return {
    facetsQuery,
    quickFiltersQuery,
    mapQuery,
    listingsQuery,
    listings,
    listingCount,
    listingPagesSettled,
    effectiveListings,
    effectiveListingCount,
  };
}
