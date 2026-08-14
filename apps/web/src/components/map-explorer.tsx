"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MapFilterControls } from "@/components/map-filter-controls";

import {
  fetchFacets,
  fetchLocationMap,
  fetchLocationOffers,
  type LocationMapFeature,
  type LocationOfferPage,
} from "@/lib/catalog-api";
import {
  DEFAULT_MAP_SEARCH_STATE,
  normalizeBbox,
  parseMapSearchParams,
  serializeMapSearchState,
  toMapLocationQuery,
  type MapSearchState,
} from "@/lib/map-search-params";

const WarsawMap = dynamic(
  () => import("@/components/warsaw-map").then((module) => module.WarsawMap),
  {
    ssr: false,
    loading: () => <div className="map-placeholder" aria-hidden="true" />,
  },
);

type OfferState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: LocationOfferPage };

export function MapExplorer() {
  const t = useTranslations("map");
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedFeatureSnapshot, setSelectedFeatureSnapshot] =
    useState<LocationMapFeature | null>(null);
  const [mapFailed, setMapFailed] = useState(false);
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

  const facetsQuery = useQuery({
    queryKey: ["filter-facets"],
    queryFn: async ({ signal }) => {
      const result = await fetchFacets({ signal });
      if (result.state === "error") throw new Error("facets");
      return result.data;
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

  const selectedFeature = useMemo(() => {
    if (selectedId === null) return null;
    return (
      mapQuery.data?.features.find((feature) => feature.id === selectedId) ??
      selectedFeatureSnapshot
    );
  }, [mapQuery.data?.features, selectedFeatureSnapshot, selectedId]);

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

  function selectLocation(locationId: string) {
    const currentFeature = mapQuery.data?.features.find(
      (feature) => feature.id === locationId,
    );
    if (currentFeature) setSelectedFeatureSnapshot(currentFeature);
    setSelectedId(locationId);
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

  return (
    <section className="map-explorer-shell" aria-label={t("explorerLabel")}>
      <MapFilterControls
        key={canonicalSearch}
        facets={facetsQuery.data ?? null}
        facetsError={facetsQuery.isError}
        facetsLoading={facetsQuery.isPending}
        state={searchState}
        onApply={(nextState) => navigate(nextState, "push")}
        onClear={() => navigate(DEFAULT_MAP_SEARCH_STATE, "push")}
      />

      <div className="map-explorer">
        <div className="map-region">
          {mapFailed ? (
            <div className="map-fallback" role="status">
              <strong>{t("mapUnavailable")}</strong>
              <span>{t("listStillAvailable")}</span>
            </div>
          ) : map ? (
            <WarsawMap
              bbox={searchState.bbox}
              data={map}
              selectedId={selectedId}
              loadingLabel={t("mapLoading")}
              onSelect={selectLocation}
              onFailure={() => setMapFailed(true)}
              onViewportChange={handleViewportChange}
            />
          ) : (
            <div
              className={`map-fallback${mapQuery.isError ? " state-error" : ""}`}
              role={mapQuery.isError ? "alert" : "status"}
            >
              <strong>{mapQuery.isError ? t("error") : t("loading")}</strong>
              {mapQuery.isError ? <span>{t("filtersPreserved")}</span> : null}
            </div>
          )}
          <p className="map-attribution">
            © OpenFreeMap · © OpenStreetMap contributors
          </p>
        </div>

        <aside className="results-panel" aria-label={t("locationsLabel")}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t("locationsEyebrow")}</p>
              <h2>{t("locationsTitle")}</h2>
            </div>
            <span className="result-count">
              {t("locationCount", {
                count: map?.meta.feature_count ?? 0,
              })}
            </span>
          </div>
          {facetsQuery.data ? (
            <p className="facet-summary">
              {t("districtCount", {
                count: facetsQuery.data.districts.length,
              })}
            </p>
          ) : null}
          {mapQuery.isFetching && map ? (
            <p className="results-status" role="status">
              {t("updating")}
            </p>
          ) : null}
          {mapQuery.isError ? (
            <p className="results-status state-error" role="alert">
              {t("error")}
            </p>
          ) : null}
          {mapQuery.isPending ? (
            <p className="results-status" role="status">
              {t("loading")}
            </p>
          ) : null}
          {map && map.features.length === 0 ? (
            <p className="results-status" role="status">
              {t("empty")}
            </p>
          ) : null}
          {map && map.features.length > 0 ? (
            <ul className="location-list">
              {map.features.map((feature) => (
                <LocationButton
                  key={feature.id}
                  feature={feature}
                  selected={feature.id === selectedId}
                  onSelect={selectLocation}
                />
              ))}
            </ul>
          ) : null}

          <OfferPanel
            feature={selectedFeature}
            offers={offers}
            onRetry={selectedId ? () => void offersQuery.refetch() : undefined}
          />
        </aside>
      </div>
    </section>
  );
}

function href(pathname: string, search: string) {
  return search ? `${pathname}?${search}` : pathname;
}

type LocationButtonProps = {
  feature: LocationMapFeature;
  selected: boolean;
  onSelect: (id: string) => void;
};

function LocationButton({ feature, selected, onSelect }: LocationButtonProps) {
  const t = useTranslations("map");
  const properties = feature.properties;
  return (
    <li>
      <button
        className="location-button"
        type="button"
        aria-pressed={selected}
        onClick={() => onSelect(feature.id)}
      >
        <span>
          <strong>{properties.display_name}</strong>
          <small>{properties.display_address}</small>
        </span>
        <span className="pin-count">
          {properties.matching_offer_count}
          <span className="sr-only"> {t("matchingOffers")}</span>
        </span>
        {properties.confidence === "low" ? (
          <span className="confidence-note">{t("lowConfidence")}</span>
        ) : null}
      </button>
    </li>
  );
}

type OfferPanelProps = {
  feature: LocationMapFeature | null;
  offers: OfferState;
  onRetry?: () => void;
};

function OfferPanel({ feature, offers, onRetry }: OfferPanelProps) {
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
            <p className="offer-area">
              {formatArea(
                offer.area_min_sqm ?? null,
                offer.area_max_sqm ?? null,
              )}
            </p>
            {offer.data_confidence === "partial" ? (
              <small>{t("partialData")}</small>
            ) : null}
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

function formatPrice(min: number | null, max: number | null) {
  if (min === null || max === null) return "Price not provided";
  const formatter = new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  });
  return min === max
    ? formatter.format(min / 100)
    : `${formatter.format(min / 100)}–${formatter.format(max / 100)}`;
}

function formatAdditionalPrice(
  min: number | null,
  max: number | null,
  included: boolean,
  includedLabel: string,
) {
  if (included) return includedLabel;
  if (min === null || max === null) return null;
  return formatPrice(min, max);
}

function formatArea(min: string | null, max: string | null) {
  if (min === null || max === null) return "Area not provided";
  return min === max ? `${min} m²` : `${min}–${max} m²`;
}
