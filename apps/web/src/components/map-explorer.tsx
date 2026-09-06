"use client";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AppliedFilterChips,
  countAppliedGroups,
} from "@/components/filter-chips";
import { MapFilterControls } from "@/components/map-filter-controls";
import { UnmappedListings } from "@/components/explorer/unmapped-listings";
import { ListingCard } from "@/components/listing-card";
import { LiveAnnouncement } from "@/components/live-announcement";
import { UserToolbar, type AuthOpener } from "@/components/user-toolbar";
import { useExplorerAccount } from "@/components/explorer/use-explorer-account";
import { useMapNavigation } from "@/components/explorer/use-map-navigation";
import { useMapCatalog } from "@/components/explorer/use-map-catalog";
import { useMapSelection } from "@/components/explorer/use-map-selection";
import { OfferPanel, type OfferState } from "@/components/explorer/offer-panel";
import { fetchLocationOffers, fetchOfferDetail } from "@/lib/catalog-api";
import { DEFAULT_MAP_SEARCH_STATE } from "@/lib/map-search-params";
import { useMediaQuery, usePrefersReducedMotion } from "@/lib/use-media-query";
import { markOfferViewed } from "@/lib/view-history-api";

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

class OfferNotFoundError extends Error {
  override name = "OfferNotFoundError";
}

export function MapExplorer() {
  const t = useTranslations("map");
  const {
    searchState,
    canonicalSearch,
    mapQueryParams,
    filtersOnlySearch,
    navigate,
    handleViewportChange,
    removeFilterGroup,
    toggleQuickFilter,
    toggleLastVisit,
    clearFiltersOnly,
    resetMapView,
  } = useMapNavigation();
  const {
    facetsQuery,
    quickFiltersQuery,
    mapQuery,
    listingsQuery,
    listings,
    listingCount,
    listingPagesSettled,
    effectiveListings,
    effectiveListingCount,
  } = useMapCatalog(canonicalSearch, mapQueryParams);
  const isMobile = useMediaQuery("(max-width: 56rem)");
  const {
    selectedId,
    selectedOfferId,
    selectedOfferMatchesFilters,
    selectedListingId,
    focusTarget,
    offerTriggerRef,
    sidebarOpen,
    setSidebarOpen,
    mobilePanelMode,
    highlightedLocationId,
    setHighlightedLocationId,
    resultsPanelRef,
    panelOpen,
    openMobileSheet,
    openMobileFullList,
    closeMobilePanel,
    selectLocation,
    selectListing,
    backToResults,
    selectOffer,
    registerOfferTrigger,
    closeOfferDetail,
    selectedFeature,
  } = useMapSelection(mapQuery.data?.features, isMobile, announceSelection);
  const [mapFailed, setMapFailed] = useState(false);
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

  const reduceMotion = usePrefersReducedMotion();
  const {
    accountQuery,
    signedIn,
    effectiveLastVisitAt,
    favoriteIds,
    toggleFavorite,
  } = useExplorerAccount();
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
  useEffect(() => {
    if (!signedIn || selectedOfferId === null || !offerDetailQuery.isSuccess) {
      return;
    }
    void markOfferViewed(selectedOfferId);
  }, [
    offerDetailQuery.dataUpdatedAt,
    offerDetailQuery.isSuccess,
    selectedOfferId,
    signedIn,
  ]);

  const announcedListingCountRef = useRef<number | null>(null);
  useEffect(() => {
    if (!listingPagesSettled) return;
    if (announcedListingCountRef.current === listingCount) return;
    announcedListingCountRef.current = listingCount;
    setLiveAnnouncement(t("listingCountAnnouncement", { count: listingCount }));
  }, [listingCount, listingPagesSettled, t]);

  function announceSelection(name: string) {
    setLiveAnnouncement(t("locationSelectedAnnouncement", { name }));
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
            lastVisitAt={effectiveLastVisitAt}
            onRemoveGroup={removeFilterGroup}
            onToggleQuickFilter={toggleQuickFilter}
            onToggleLastVisit={toggleLastVisit}
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
                        onToggleStar={toggleFavorite}
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
              <UnmappedListings
                query={mapQueryParams}
                onOfferTrigger={registerOfferTrigger}
                onSelectOffer={selectOffer}
                favoriteIds={favoriteIds}
                signedIn={signedIn}
                onToggleStar={toggleFavorite}
              />
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
                onOfferTrigger={registerOfferTrigger}
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
