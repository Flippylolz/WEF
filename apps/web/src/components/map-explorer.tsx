"use client";

import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  AppliedFilterChips,
  countAppliedGroups,
  type FilterChipGroup,
} from "@/components/filter-chips";
import { MapFilterControls } from "@/components/map-filter-controls";
import { ListingCard } from "@/components/listing-card";
import { LiveAnnouncement } from "@/components/live-announcement";
import { UserToolbar, type AuthOpener } from "@/components/user-toolbar";

import {
  fetchFacets,
  fetchLocationMap,
  fetchLocationOffers,
  fetchOfferDetail,
  fetchQuickFilters,
  fetchViewportListings,
  type LocationMapFeature,
  type LocationOfferPage,
  type ViewportListing,
} from "@/lib/catalog-api";
import {
  addFavorite,
  fetchFavorites,
  removeFavorite,
} from "@/lib/favorites-api";
import { fetchCurrentAccount } from "@/lib/auth-api";
import {
  DEFAULT_BBOX,
  DEFAULT_CONTENT_TYPES,
  DEFAULT_MAP_SEARCH_STATE,
  normalizeBbox,
  parseMapSearchParams,
  serializeMapSearchState,
  toMapLocationQuery,
  type MapSearchState,
} from "@/lib/map-search-params";
import {
  formatAdditionalPrice,
  formatArea,
  formatPrice,
} from "@/lib/offer-presentation";
import type { FocusTarget } from "@/lib/listing-focus";
import { useMediaQuery, usePrefersReducedMotion } from "@/lib/use-media-query";

type MobilePanelMode = "map" | "sheet" | "full";

const LISTING_PAGE_SIZE = 20;

const WarsawMap = dynamic(
  () => import("@/components/warsaw-map").then((module) => module.WarsawMap),
  {
    ssr: false,
    loading: () => <div className="map-placeholder" aria-hidden="true" />,
  },
);

const OfferDetailDrawer = dynamic(
  () =>
    import("@/components/offer-detail-drawer").then(
      (module) => module.OfferDetailDrawer,
    ),
  { ssr: false },
);

type OfferState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: LocationOfferPage };

class OfferNotFoundError extends Error {
  override name = "OfferNotFoundError";
}

export function MapExplorer() {
  const t = useTranslations("map");
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawSearch = searchParams.toString();
  const searchState = useMemo(
    () => parseMapSearchParams(new URLSearchParams(rawSearch)),
    [rawSearch],
  );
  const canonicalSearch = useMemo(
    () => serializeMapSearchState(searchState),
    [searchState],
  );
  const mapQueryParams = useMemo(
    () => toMapLocationQuery(searchState),
    [searchState],
  );
  const filtersOnlySearch = useMemo(() => {
    const params = new URLSearchParams(canonicalSearch);
    params.delete("bbox");
    return params.toString();
  }, [canonicalSearch]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [selectedOfferMatchesFilters, setSelectedOfferMatchesFilters] =
    useState<boolean | null>(null);
  const [selectedListingId, setSelectedListingId] = useState<string | null>(
    null,
  );
  const [focusTarget, setFocusTarget] = useState<FocusTarget | null>(null);
  const offerTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [selectedFeatureSnapshot, setSelectedFeatureSnapshot] =
    useState<LocationMapFeature | null>(null);
  const [mapFailed, setMapFailed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobilePanelMode, setMobilePanelMode] =
    useState<MobilePanelMode>("map");
  const [highlightedLocationId, setHighlightedLocationId] = useState<
    string | null
  >(null);
  const resultsPanelRef = useRef<HTMLElement | null>(null);
  const resultsScrollRef = useRef<number>(0);
  const resultsTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [liveAnnouncement, setLiveAnnouncement] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filtersDialogRef = useRef<HTMLDialogElement | null>(null);
  const openAuthRef = useRef<AuthOpener>(() => undefined);
  const registerAuthOpener = useCallback((open: AuthOpener) => {
    openAuthRef.current = open;
  }, []);

  useEffect(() => {
    const dialog = filtersDialogRef.current;
    if (dialog === null) return;
    if (filtersOpen && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
    }
    if (!filtersOpen && dialog.open) {
      dialog.close();
    }
  }, [filtersOpen]);

  const resultsRestorationNonce = selectedId === null ? 1 : 0;
  useEffect(() => {
    if (selectedId !== null) return;
    if (resultsScrollRef.current === 0 && resultsTriggerRef.current === null) {
      return;
    }
    const panel = resultsPanelRef.current;
    if (panel !== null) {
      panel.scrollTop = resultsScrollRef.current;
    }
    resultsTriggerRef.current?.focus();
    resultsScrollRef.current = 0;
    resultsTriggerRef.current = null;
    // The nonce marks the transition back into the results list.
  }, [resultsRestorationNonce, selectedId]);
  const isMobile = useMediaQuery("(max-width: 56rem)");
  const reduceMotion = usePrefersReducedMotion();
  const viewportTimer = useRef<number | null>(null);
  const cancelViewportUpdate = useCallback(() => {
    if (viewportTimer.current !== null) {
      window.clearTimeout(viewportTimer.current);
      viewportTimer.current = null;
    }
  }, []);

  useEffect(() => {
    cancelViewportUpdate();
    if (rawSearch !== canonicalSearch) {
      router.replace(href(pathname, canonicalSearch), { scroll: false });
    }
  }, [cancelViewportUpdate, canonicalSearch, pathname, rawSearch, router]);

  useEffect(() => {
    return cancelViewportUpdate;
  }, [cancelViewportUpdate]);

  const panelOpen = isMobile ? mobilePanelMode !== "map" : sidebarOpen;

  function openMobileSheet() {
    setMobilePanelMode("sheet");
  }

  function openMobileFullList() {
    setMobilePanelMode("full");
  }

  function closeMobilePanel() {
    setMobilePanelMode("map");
  }

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
  const accountQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async ({ signal }) => {
      const result = await fetchCurrentAccount({ signal });
      if (result.state === "error") throw new Error("auth");
      return result.data;
    },
  });
  const signedIn = accountQuery.isSuccess && accountQuery.data !== null;
  const favoritesQuery = useQuery({
    queryKey: ["favorites"],
    enabled: signedIn,
    queryFn: async ({ signal }) => {
      const result = await fetchFavorites({ signal });
      if (result.state === "error") throw new Error("favorites");
      return result.data.items;
    },
  });
  const favoriteIds = useMemo(
    () =>
      new Set(
        (favoritesQuery.data ?? []).map((item) => String(item.location_id)),
      ),
    [favoritesQuery.data],
  );
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
  const offersQuery = useQuery({
    queryKey: ["location-offers", selectedId, canonicalSearch],
    enabled: selectedId !== null,
    queryFn: async ({ signal }) => {
      if (selectedId === null) throw new Error("missing location");
      const result = await fetchLocationOffers(selectedId, mapQueryParams, {
        signal,
      });
      if (result.state === "error") throw new Error("offers");
      return result.data;
    },
  });
  const offerDetailQuery = useQuery({
    queryKey: ["offer-detail", selectedOfferId],
    enabled: selectedOfferId !== null,
    queryFn: async ({ signal }) => {
      if (selectedOfferId === null) throw new Error("missing offer");
      const result = await fetchOfferDetail(selectedOfferId, { signal });
      if (result.state === "not_found") throw new OfferNotFoundError();
      if (result.state === "error") throw new Error("offer-detail");
      return result.data;
    },
  });

  const selectedFeature = useMemo(() => {
    if (selectedId === null) return null;
    return (
      mapQuery.data?.features.find((feature) => feature.id === selectedId) ??
      selectedFeatureSnapshot
    );
  }, [mapQuery.data?.features, selectedFeatureSnapshot, selectedId]);

  const announcedListingCountRef = useRef<number | null>(null);
  useEffect(() => {
    if (!listingPagesSettled) return;
    if (announcedListingCountRef.current === listingCount) return;
    announcedListingCountRef.current = listingCount;
    setLiveAnnouncement(t("listingCountAnnouncement", { count: listingCount }));
  }, [listingCount, listingPagesSettled, t]);

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

  const navigate = useCallback(
    (nextState: MapSearchState, mode: "push" | "replace") => {
      cancelViewportUpdate();
      const nextSearch = serializeMapSearchState(nextState);
      if (nextSearch === canonicalSearch) return;
      router[mode](href(pathname, nextSearch), { scroll: false });
    },
    [cancelViewportUpdate, canonicalSearch, pathname, router],
  );

  const handleViewportChange = useCallback(
    (bbox: string) => {
      const normalized = normalizeBbox(bbox);
      cancelViewportUpdate();
      if (normalized === null || normalized === searchState.bbox) return;
      viewportTimer.current = window.setTimeout(() => {
        viewportTimer.current = null;
        navigate({ ...searchState, bbox: normalized }, "replace");
      }, 300);
    },
    [cancelViewportUpdate, navigate, searchState],
  );

  const removeFilterGroup = useCallback(
    (group: FilterChipGroup) => {
      const next = { ...searchState };
      if (group === "price") {
        next.priceMinMinor = null;
        next.priceMaxMinor = null;
      } else if (group === "area") {
        next.areaMin = null;
        next.areaMax = null;
      } else if (group === "rooms") {
        next.rooms = [];
      } else if (group === "districts") {
        next.districts = [];
      } else if (group === "marketTypes") {
        next.marketTypes = [];
      } else if (group === "contentTypes") {
        next.contentTypes = DEFAULT_CONTENT_TYPES;
      } else if (group === "publication") {
        next.publishedFrom = null;
        next.publishedTo = null;
      } else if (group === "quickFilter") {
        next.quickFilter = null;
      }
      navigate(next, "push");
    },
    [navigate, searchState],
  );

  const toggleQuickFilter = useCallback(
    (presetId: string | null) => {
      navigate(
        {
          ...searchState,
          quickFilter: presetId,
          publishedFrom: presetId ? null : searchState.publishedFrom,
        },
        "push",
      );
    },
    [navigate, searchState],
  );

  function selectLocation(locationId: string) {
    const currentFeature = mapQuery.data?.features.find(
      (feature) => feature.id === locationId,
    );
    if (currentFeature) {
      setSelectedFeatureSnapshot(currentFeature);
      setLiveAnnouncement(
        t("locationSelectedAnnouncement", {
          name: currentFeature.properties.display_name,
        }),
      );
    }
    if (selectedId === null) {
      resultsScrollRef.current =
        resultsPanelRef.current?.scrollTop ?? resultsScrollRef.current;
    }
    setSelectedId(locationId);
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
    if (isMobile) {
      openMobileSheet();
    } else {
      setSidebarOpen(true);
    }
  }

  function selectListing(listing: ViewportListing, trigger: HTMLButtonElement) {
    resultsTriggerRef.current = trigger;
    setSelectedListingId(listing.id);
    setFocusTarget({
      longitude: listing.location.geometry.coordinates[0],
      latitude: listing.location.geometry.coordinates[1],
      nonce: Date.now(),
    });
    selectLocation(listing.location.id);
  }

  function backToResults() {
    setSelectedId(null);
    setSelectedListingId(null);
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
    if (isMobile) {
      setMobilePanelMode("full");
    }
  }

  function clearFiltersOnly() {
    navigate(
      {
        ...DEFAULT_MAP_SEARCH_STATE,
        bbox: searchState.bbox,
      },
      "push",
    );
  }

  function resetMapView() {
    navigate({ ...searchState, bbox: DEFAULT_BBOX }, "push");
  }

  function selectOffer(
    offerId: string,
    matchesFilters: boolean,
    trigger: HTMLButtonElement,
  ) {
    offerTriggerRef.current = trigger;
    setSelectedOfferId(offerId);
    setSelectedOfferMatchesFilters(matchesFilters);
  }

  function closeOfferDetail() {
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
  }

  function retryMap() {
    setMapFailed(false);
    void mapQuery.refetch();
  }

  const offers: OfferState =
    selectedId === null
      ? { status: "idle" }
      : offersQuery.isPending
        ? { status: "loading" }
        : offersQuery.isError || offersQuery.data === undefined
          ? { status: "error" }
          : { status: "ready", data: offersQuery.data };
  const map = mapQuery.data;
  const explorerClassName = [
    "map-explorer",
    !isMobile && !sidebarOpen ? "map-explorer-collapsed" : "",
    isMobile ? "map-explorer-mobile" : "",
    isMobile ? `map-panel-${mobilePanelMode}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const appliedFilterCount = useMemo(
    () => countAppliedGroups(searchState),
    [searchState],
  );

  return (
    <section className="map-explorer-shell" aria-label={t("explorerLabel")}>
      <LiveAnnouncement message={liveAnnouncement} />
      <header className="app-bar">
        <p className="app-title">
          <span aria-hidden="true">WEF</span>
        </p>
        <button
          className="filters-toggle"
          type="button"
          aria-haspopup="dialog"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen(true)}
        >
          {t("filtersButton")}
          {appliedFilterCount > 0 ? (
            <span className="filters-toggle-count">{appliedFilterCount}</span>
          ) : null}
        </button>
        <span className="app-bar-spacer" />
        <UserToolbar
          onSelectFavorite={selectLocation}
          onRegisterAuthOpener={registerAuthOpener}
        />
      </header>
      <div className={explorerClassName}>
        <aside
          id="explorer-sidebar"
          className={`explorer-sidebar${panelOpen ? "" : " explorer-sidebar-collapsed"}`}
          aria-label={t("panelLabel")}
          inert={!panelOpen}
        >
          {isMobile ? (
            <div className="mobile-panel-toolbar">
              {mobilePanelMode === "sheet" ? (
                <button type="button" onClick={openMobileFullList}>
                  {t("mobileFullList")}
                </button>
              ) : null}
              <button type="button" onClick={closeMobilePanel}>
                {t("mobileShowMap")}
              </button>
            </div>
          ) : null}
          <AppliedFilterChips
            state={searchState}
            quickFilters={quickFiltersQuery.data ?? []}
            quickFiltersLoading={quickFiltersQuery.isPending}
            onRemoveGroup={removeFilterGroup}
            onToggleQuickFilter={toggleQuickFilter}
            onOpenFilters={() => setFiltersOpen(true)}
          />

          {selectedId === null ? (
            <section
              ref={resultsPanelRef}
              className="results-panel"
              aria-label={t("listingsLabel")}
            >
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{t("listingsEyebrow")}</p>
                  <h2>{t("listingsTitle")}</h2>
                  <span className="results-scope">{t("resultsScope")}</span>
                </div>
                <div className="panel-heading-tools">
                  <span className="result-count">
                    {t("listingCount", { count: effectiveListingCount })}
                  </span>
                  {isMobile ? null : (
                    <button
                      className="sidebar-toggle"
                      type="button"
                      aria-label={t("hidePanel")}
                      title={t("hidePanel")}
                      aria-expanded={sidebarOpen}
                      aria-controls="explorer-sidebar"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <ChevronRightIcon />
                    </button>
                  )}
                </div>
              </div>
              {listingsQuery.isFetching && effectiveListings.length > 0 ? (
                <p className="results-status" role="status">
                  {t("updating")}
                </p>
              ) : null}
              {listingsQuery.isError ? (
                <div className="results-status state-error" role="alert">
                  <p>{t("listingsError")}</p>
                  <button
                    className="retry-button"
                    type="button"
                    onClick={() => void listingsQuery.refetch()}
                  >
                    {t("retry")}
                  </button>
                </div>
              ) : null}
              {listingsQuery.isPending ? (
                <>
                  <p className="results-status" role="status">
                    {t("loading")}
                  </p>
                  <ul className="location-list" aria-hidden="true">
                    {Array.from({ length: 5 }, (_, index) => (
                      <li className="listing-skeleton" key={index} />
                    ))}
                  </ul>
                </>
              ) : null}
              {listingPagesSettled && listings.length === 0 ? (
                <div className="results-status" role="status">
                  <p>{t("listingsEmpty")}</p>
                  <div className="empty-actions">
                    <button type="button" onClick={clearFiltersOnly}>
                      {t("clearFilters")}
                    </button>
                    <button type="button" onClick={resetMapView}>
                      {t("resetMap")}
                    </button>
                  </div>
                </div>
              ) : null}
              {effectiveListings.length > 0 ? (
                <>
                  <ul className="location-list" aria-label={t("listingsLabel")}>
                    {effectiveListings.map((listing) => (
                      <ListingCard
                        key={listing.id}
                        listing={listing}
                        selected={listing.id === selectedListingId}
                        highlighted={
                          listing.location.id === highlightedLocationId
                        }
                        starred={favoriteIds.has(String(listing.location.id))}
                        showStar={signedIn}
                        onSelect={selectListing}
                        onHighlight={setHighlightedLocationId}
                        onToggleStar={async (locationId) => {
                          const starred = favoriteIds.has(locationId);
                          const result = starred
                            ? await removeFavorite(locationId)
                            : await addFavorite(locationId);
                          if (result.state === "ready") {
                            await queryClient.invalidateQueries({
                              queryKey: ["favorites"],
                            });
                          }
                        }}
                      />
                    ))}
                  </ul>
                  {listingsQuery.hasNextPage ? (
                    <button
                      className="load-more"
                      type="button"
                      disabled={listingsQuery.isFetchingNextPage}
                      onClick={() => void listingsQuery.fetchNextPage()}
                    >
                      {listingsQuery.isFetchingNextPage
                        ? t("loadingMore")
                        : t("loadMore")}
                    </button>
                  ) : null}
                </>
              ) : null}
            </section>
          ) : (
            <section className="results-panel" aria-label={t("locationsLabel")}>
              <button
                className="back-to-results"
                type="button"
                onClick={backToResults}
              >
                <ChevronLeftIcon />
                {t("backToResults")}
              </button>
              <OfferPanel
                feature={selectedFeature}
                offers={offers}
                onRetry={
                  selectedId ? () => void offersQuery.refetch() : undefined
                }
                onSelectOffer={selectOffer}
              />
              {isMobile ? null : (
                <button
                  className="sidebar-toggle selected-view-toggle"
                  type="button"
                  aria-label={t("hidePanel")}
                  title={t("hidePanel")}
                  aria-expanded={sidebarOpen}
                  aria-controls="explorer-sidebar"
                  onClick={() => setSidebarOpen(false)}
                >
                  <ChevronRightIcon />
                </button>
              )}
            </section>
          )}
        </aside>

        <div className="map-region">
          {mapFailed ? (
            <div className="map-fallback" role="status">
              <strong>{t("mapUnavailable")}</strong>
              <span>{t("listStillAvailable")}</span>
              <button type="button" onClick={retryMap}>
                {t("retryMap")}
              </button>
            </div>
          ) : map ? (
            <WarsawMap
              key="warsaw-map"
              bbox={searchState.bbox}
              data={map}
              selectedId={selectedId}
              highlightedId={highlightedLocationId}
              focusTarget={focusTarget}
              loadingLabel={t("mapLoading")}
              onSelect={selectLocation}
              onFailure={() => setMapFailed(true)}
              onViewportChange={handleViewportChange}
              reduceMotion={reduceMotion}
            />
          ) : (
            <div
              className={`map-fallback${mapQuery.isError ? " state-error" : ""}`}
              role={mapQuery.isError ? "alert" : "status"}
            >
              <strong>{mapQuery.isError ? t("error") : t("loading")}</strong>
              {mapQuery.isError ? (
                <>
                  <span>{t("filtersPreserved")}</span>
                  <button type="button" onClick={retryMap}>
                    {t("retryMap")}
                  </button>
                </>
              ) : null}
            </div>
          )}
          {!sidebarOpen && !isMobile ? (
            <button
              className="sidebar-toggle sidebar-toggle-floating"
              type="button"
              aria-label={t("showPanel")}
              title={t("showPanel")}
              aria-expanded={false}
              aria-controls="explorer-sidebar"
              onClick={() => setSidebarOpen(true)}
            >
              <ChevronLeftIcon />
            </button>
          ) : null}
          {isMobile && mobilePanelMode === "map" ? (
            <div
              className="mobile-results-bar"
              role="region"
              aria-label={t("mobileResultsBarLabel")}
            >
              <button type="button" onClick={openMobileSheet}>
                {t("mobileShowListings", { count: effectiveListingCount })}
              </button>
            </div>
          ) : null}
        </div>
      </div>
      <dialog
        ref={filtersDialogRef}
        className="filter-drawer"
        aria-label={t("filtersTitle")}
        onClose={() => setFiltersOpen(false)}
        onClick={(event) => {
          if (event.target === filtersDialogRef.current) {
            setFiltersOpen(false);
          }
        }}
      >
        <div className="filter-drawer-body">
          <MapFilterControls
            key={filtersOnlySearch}
            facets={facetsQuery.data ?? null}
            facetsError={facetsQuery.isError}
            facetsLoading={facetsQuery.isPending}
            state={searchState}
            onApply={(nextState) => {
              navigate({ ...nextState, bbox: searchState.bbox }, "push");
              setFiltersOpen(false);
            }}
            onClear={() => {
              navigate(DEFAULT_MAP_SEARCH_STATE, "push");
              setFiltersOpen(false);
            }}
          />
        </div>
      </dialog>
      <OfferDetailDrawer
        open={selectedOfferId !== null}
        offerId={selectedOfferId}
        matchesFilters={selectedOfferMatchesFilters}
        detailQuery={offerDetailQuery}
        account={accountQuery.data}
        onClose={closeOfferDetail}
        onRetry={
          selectedOfferId ? () => void offerDetailQuery.refetch() : undefined
        }
        onRequestSignIn={() => openAuthRef.current({ mode: "login" })}
        onRequestPasswordChange={() =>
          openAuthRef.current({ mode: "password" })
        }
        returnFocusRef={offerTriggerRef}
      />
    </section>
  );
}

function ChevronLeftIcon() {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height="16"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
      width="16"
    >
      <path d="m15 6-6 6 6 6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height="16"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
      width="16"
    >
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

function href(pathname: string, search: string) {
  return search ? `${pathname}?${search}` : pathname;
}

type OfferPanelProps = {
  feature: LocationMapFeature | null;
  offers: OfferState;
  onRetry?: () => void;
  onSelectOffer: (
    offerId: string,
    matchesFilters: boolean,
    trigger: HTMLButtonElement,
  ) => void;
};

function OfferPanel({
  feature,
  offers,
  onRetry,
  onSelectOffer,
}: OfferPanelProps) {
  const t = useTranslations("map");
  if (!feature) {
    return <p className="offer-placeholder">{t("selectLocation")}</p>;
  }
  if (offers.status === "loading") {
    return (
      <p className="offer-placeholder" role="status">
        {t("offersLoading")}
      </p>
    );
  }
  if (offers.status === "error") {
    return (
      <div className="offer-placeholder state-error" role="alert">
        <p>{t("offersError")}</p>
        {onRetry ? (
          <button type="button" onClick={onRetry}>
            {t("retry")}
          </button>
        ) : null}
      </div>
    );
  }
  if (offers.status !== "ready" || offers.data.items.length === 0) {
    return <p className="offer-placeholder">{t("offersEmpty")}</p>;
  }

  return (
    <section className="offer-panel" aria-labelledby="offer-panel-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t("selectedEyebrow")}</p>
          <h3 id="offer-panel-title">{feature.properties.display_name}</h3>
        </div>
        <span className="result-count">
          {t("offerCountSummary", {
            matching: offers.data.matching_count,
            total: offers.data.total_count,
          })}
        </span>
      </div>
      <ul className="offer-list">
        {offers.data.items.map((offer) => (
          <li
            key={offer.id}
            className={`offer-card${offer.matches_filters ? "" : " offer-card-nonmatching"}`}
          >
            <div className="offer-card-heading">
              <strong>{offer.display_name}</strong>
              <time dateTime={offer.published_at}>
                {new Intl.DateTimeFormat("en-GB", {
                  dateStyle: "medium",
                }).format(new Date(offer.published_at))}
              </time>
            </div>
            {!offer.matches_filters ? (
              <p className="nonmatching-note">{t("nonMatchingOffer")}</p>
            ) : null}
            <dl className="offer-prices">
              <PriceRow
                label={t("apartmentPrice")}
                value={formatPrice(
                  offer.price_min_minor ?? null,
                  offer.price_max_minor ?? null,
                )}
              />
              <PriceRow
                label={t("parkingPrice")}
                value={formatAdditionalPrice(
                  offer.parking_price_min_minor ?? null,
                  offer.parking_price_max_minor ?? null,
                  offer.parking_included_in_price ?? false,
                  t("includedInApartmentPrice"),
                )}
              />
              <PriceRow
                label={t("storagePrice")}
                value={formatAdditionalPrice(
                  offer.storage_price_min_minor ?? null,
                  offer.storage_price_max_minor ?? null,
                  offer.storage_included_in_price ?? false,
                  t("includedInApartmentPrice"),
                )}
              />
            </dl>
            {formatArea(
              offer.area_min_sqm ?? null,
              offer.area_max_sqm ?? null,
            ) ? (
              <p className="offer-area">
                {formatArea(
                  offer.area_min_sqm ?? null,
                  offer.area_max_sqm ?? null,
                )}
              </p>
            ) : null}
            {offer.data_confidence === "partial" ? (
              <small>{t("partialData")}</small>
            ) : null}
            <button
              className="offer-detail-trigger"
              type="button"
              onClick={(event) =>
                onSelectOffer(
                  offer.id,
                  offer.matches_filters,
                  event.currentTarget,
                )
              }
            >
              {t("viewOfferDetails", { name: offer.display_name })}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

type PriceRowProps = {
  label: string;
  value: string | null;
};

function PriceRow({ label, value }: PriceRowProps) {
  if (value === null) return null;
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
