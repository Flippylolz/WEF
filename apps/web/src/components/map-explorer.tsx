"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import {
  fetchFacets,
  fetchLocationMap,
  fetchLocationOffers,
  type FilterFacets,
  type LocationMap,
  type LocationMapFeature,
  type LocationOfferPage,
} from "@/lib/catalog-api";

const WarsawMap = dynamic(
  () => import("@/components/warsaw-map").then((module) => module.WarsawMap),
  {
    ssr: false,
    loading: () => <div className="map-placeholder" aria-hidden="true" />,
  },
);

type CatalogState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; map: LocationMap; facets: FilterFacets };

type OfferState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: LocationOfferPage };

export function MapExplorer() {
  const t = useTranslations("map");
  const [catalog, setCatalog] = useState<CatalogState>({ status: "loading" });
  const [offers, setOffers] = useState<OfferState>({ status: "idle" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapFailed, setMapFailed] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadCatalog() {
      const [mapResult, facetResult] = await Promise.all([
        fetchLocationMap(),
        fetchFacets(),
      ]);
      if (!active) return;
      if (mapResult.state === "error" || facetResult.state === "error") {
        setCatalog({ status: "error" });
        return;
      }
      setCatalog({
        status: "ready",
        map: mapResult.data,
        facets: facetResult.data,
      });
    }
    void loadCatalog();
    return () => {
      active = false;
    };
  }, []);

  const selectedFeature = useMemo(() => {
    if (catalog.status !== "ready" || selectedId === null) return null;
    return (
      catalog.map.features.find((feature) => feature.id === selectedId) ?? null
    );
  }, [catalog, selectedId]);

  async function selectLocation(locationId: string) {
    setSelectedId(locationId);
    setOffers({ status: "loading" });
    const result = await fetchLocationOffers(locationId);
    setOffers(
      result.state === "ready"
        ? { status: "ready", data: result.data }
        : { status: "error" },
    );
  }

  if (catalog.status === "loading") {
    return (
      <p className="state-message" role="status">
        {t("loading")}
      </p>
    );
  }

  if (catalog.status === "error") {
    return (
      <p className="state-message state-error" role="alert">
        {t("error")}
      </p>
    );
  }

  if (catalog.map.features.length === 0) {
    return (
      <p className="state-message" role="status">
        {t("empty")}
      </p>
    );
  }

  return (
    <section className="map-explorer" aria-label={t("explorerLabel")}>
      <div className="map-region">
        {mapFailed ? (
          <div className="map-fallback" role="status">
            <strong>{t("mapUnavailable")}</strong>
            <span>{t("listStillAvailable")}</span>
          </div>
        ) : (
          <WarsawMap
            data={catalog.map}
            selectedId={selectedId}
            onSelect={(id) => void selectLocation(id)}
            onFailure={() => setMapFailed(true)}
          />
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
            {t("locationCount", { count: catalog.map.meta.feature_count })}
          </span>
        </div>
        <p className="facet-summary">
          {t("districtCount", { count: catalog.facets.districts.length })}
        </p>
        <ul className="location-list">
          {catalog.map.features.map((feature) => (
            <LocationButton
              key={feature.id}
              feature={feature}
              selected={feature.id === selectedId}
              onSelect={selectLocation}
            />
          ))}
        </ul>

        <OfferPanel
          feature={selectedFeature}
          offers={offers}
          onRetry={
            selectedId ? () => void selectLocation(selectedId) : undefined
          }
        />
      </aside>
    </section>
  );
}

type LocationButtonProps = {
  feature: LocationMapFeature;
  selected: boolean;
  onSelect: (id: string) => Promise<void>;
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
        onClick={() => void onSelect(feature.id)}
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
          {offers.data.matching_count}/{offers.data.total_count}
        </span>
      </div>
      <ul className="offer-list">
        {offers.data.items.map((offer) => (
          <li key={offer.id} className="offer-card">
            <div className="offer-card-heading">
              <strong>{offer.display_name}</strong>
              <time dateTime={offer.published_at}>
                {new Intl.DateTimeFormat("en-GB", {
                  dateStyle: "medium",
                }).format(new Date(offer.published_at))}
              </time>
            </div>
            <p>
              {formatPrice(
                offer.price_min_minor ?? null,
                offer.price_max_minor ?? null,
              )}
              {" · "}
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

function formatArea(min: string | null, max: string | null) {
  if (min === null || max === null) return "Area not provided";
  return min === max ? `${min} m²` : `${min}–${max} m²`;
}
