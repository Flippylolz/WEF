"use client";

import { useTranslations } from "next-intl";
import { formatArea, formatPrice, formatRooms } from "@/lib/offer-presentation";

import type { ViewportListing } from "@/lib/catalog-api";

type ListingCardProps = {
  listing: ViewportListing;
  selected: boolean;
  highlighted: boolean;
  starred: boolean;
  showStar: boolean;
  onSelect: (listing: ViewportListing, trigger: HTMLButtonElement) => void;
  onHighlight: (locationId: string | null) => void;
  onToggleStar: (locationId: string) => void;
};

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
});

export function ListingCard({
  listing,
  selected,
  highlighted,
  starred,
  showStar,
  onSelect,
  onHighlight,
  onToggleStar,
}: ListingCardProps) {
  const t = useTranslations("map");
  const location = listing.location;
  const price = formatPrice(
    listing.price_min_minor ?? null,
    listing.price_max_minor ?? null,
  );
  const area = formatArea(
    listing.area_min_sqm ?? null,
    listing.area_max_sqm ?? null,
  );
  const rooms = formatRooms(
    listing.rooms_min ?? null,
    listing.rooms_max ?? null,
  );
  const lowConfidence = location.confidence === "low";

  return (
    <li>
      <div className="location-button-row">
        <button
          className={`listing-card${highlighted ? " listing-card-highlighted" : ""}`}
          type="button"
          aria-pressed={selected}
          onClick={(event) => onSelect(listing, event.currentTarget)}
          onFocus={() => onHighlight(location.id)}
          onBlur={() => onHighlight(null)}
          onMouseEnter={() => onHighlight(location.id)}
          onMouseLeave={() => onHighlight(null)}
        >
          <span className="listing-card-heading">
            <strong>{location.display_name}</strong>
            <time dateTime={listing.published_at}>
              {t("publishedOn", {
                date: dateFormatter.format(new Date(listing.published_at)),
              })}
            </time>
          </span>
          <small className="listing-card-address">
            {location.display_address}
          </small>
          <span className="listing-card-meta">
            {price ? (
              <strong className="listing-card-price">{price}</strong>
            ) : null}
            {area ? <span>{area}</span> : null}
            {rooms ? (
              <span>
                {rooms === "1"
                  ? t("listingRoom", { rooms })
                  : t("listingRooms", { rooms })}
              </span>
            ) : null}
            <span>{t(`marketType.${listing.market_type}`)}</span>
            <span>{t(`contentType.${listing.content_type}`)}</span>
          </span>
          {lowConfidence ? (
            <span className="confidence-note">{t("lowConfidence")}</span>
          ) : null}
          {listing.data_confidence === "partial" ? (
            <span className="listing-card-partial">{t("partialData")}</span>
          ) : null}
        </button>
        {showStar ? (
          <button
            className={`location-star-button${starred ? " location-star-button-active" : ""}`}
            type="button"
            aria-label={starred ? t("unstarLocation") : t("starLocation")}
            aria-pressed={starred}
            onClick={(event) => {
              event.stopPropagation();
              onToggleStar(location.id);
            }}
          >
            ★
          </button>
        ) : null}
      </div>
    </li>
  );
}
