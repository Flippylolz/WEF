import { useTranslations } from "next-intl";
import type { LocationMapFeature, LocationOfferPage } from "@/lib/catalog-api";
import {
  formatAdditionalPrice,
  formatArea,
  formatPrice,
} from "@/lib/offer-presentation";

export type OfferState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: LocationOfferPage };

type OfferPanelProps = {
  feature: LocationMapFeature | null;
  offers: OfferState;
  onRetry?: () => void;
  onOfferTrigger: (offerId: string, trigger: HTMLButtonElement | null) => void;
  onSelectOffer: (
    offerId: string,
    matchesFilters: boolean,
    trigger: HTMLButtonElement,
  ) => void;
};

export function OfferPanel({
  feature,
  offers,
  onRetry,
  onSelectOffer,
  onOfferTrigger,
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
              ref={(node) => onOfferTrigger(offer.id, node)}
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
