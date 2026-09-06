import { useTranslations } from "next-intl";
import { OfferMediaGallery } from "@/components/offer-media-gallery";
import type { Account } from "@/lib/auth-api";
import type { OfferDetail } from "@/lib/catalog-api";
import {
  formatAdditionalPrice,
  formatArea,
  formatPrice,
  formatPublishedDate,
  formatRooms,
  isSafeExternalUrl,
} from "@/lib/offer-presentation";
import { ContactRevealSection } from "./contact-reveal-section";

// Parser extraction field names (e2-v7) mapped to i18n keys. Fields outside
// this map fall back to their raw name so unseen parser fields stay visible.
const detailFieldLabelKeys: Record<string, string> = {
  apartment_price: "detailFieldApartmentPrice",
  content_type: "detailFieldContentType",
  market_type: "detailFieldMarket",
  location: "detailFieldLocation",
  district: "detailFieldDistrict",
  development_name: "detailFieldDevelopment",
  parking: "detailFieldParking",
  storage: "detailFieldStorage",
  area_sqm: "detailFieldArea",
  rooms: "detailFieldRooms",
  floor: "detailFieldFloor",
  delivery: "detailFieldDelivery",
  contacts: "detailFieldContacts",
};

type OfferDetailContentProps = {
  detail: OfferDetail;
  matchesFilters: boolean | null;
  account: Account | null | undefined;
  onRequestSignIn: () => void;
  onRequestPasswordChange: () => void;
};

export function OfferDetailContent({
  detail,
  matchesFilters,
  account,
  onRequestSignIn,
  onRequestPasswordChange,
}: OfferDetailContentProps) {
  const t = useTranslations("map");
  const area = formatArea(
    detail.area_min_sqm ?? null,
    detail.area_max_sqm ?? null,
  );
  const rooms = formatRooms(detail.rooms_min ?? null, detail.rooms_max ?? null);
  const verifiedLink = isSafeExternalUrl(detail.verified_source_url)
    ? detail.verified_source_url
    : null;

  return (
    <div className="offer-detail-body">
      <section aria-label={t("detailPublicationLabel")}>
        <h3>{t("detailPublicationLabel")}</h3>
        <p className="offer-detail-published">
          <time dateTime={detail.published_at}>
            {formatPublishedDate(detail.published_at)}
          </time>
        </p>
        <p className="offer-detail-disclaimer">
          {t("detailAvailabilityDisclaimer")}
        </p>
        {matchesFilters === false ? (
          <p className="nonmatching-note">{t("nonMatchingOffer")}</p>
        ) : null}
      </section>

      <dl className="offer-detail-fields">
        <DetailRow
          label={t("contentTypeLabel")}
          value={t(`contentType.${detail.content_type}`)}
        />
        <DetailRow
          label={t("marketTypeLabel")}
          value={t(`marketType.${detail.market_type}`)}
        />
        <DetailRow
          label={t("propertyTypeLabel")}
          value={t(`propertyType.${detail.property_type}`)}
        />
        <DetailRow
          label={t("apartmentPrice")}
          value={formatPrice(
            detail.price_min_minor ?? null,
            detail.price_max_minor ?? null,
          )}
        />
        <DetailRow
          label={t("parkingPrice")}
          value={formatAdditionalPrice(
            detail.parking_price_min_minor ?? null,
            detail.parking_price_max_minor ?? null,
            detail.parking_included_in_price,
            t("includedInApartmentPrice"),
          )}
        />
        <DetailRow
          label={t("storagePrice")}
          value={formatAdditionalPrice(
            detail.storage_price_min_minor ?? null,
            detail.storage_price_max_minor ?? null,
            detail.storage_included_in_price,
            t("includedInApartmentPrice"),
          )}
        />
        <DetailRow label={t("detailAreaLabel")} value={area} />
        <DetailRow label={t("detailRoomsLabel")} value={rooms} />
        <DetailRow label={t("detailFloorLabel")} value={detail.floor_label} />
        <DetailRow
          label={t("detailDeliveryLabel")}
          value={detail.delivery_label}
        />
      </dl>

      {detail.data_confidence === "partial" ? (
        <p className="offer-detail-note">{t("partialData")}</p>
      ) : null}
      {detail.data_origin === "ai_assisted" ? (
        <p className="offer-detail-note">{t("aiAssistedData")}</p>
      ) : null}

      <section aria-label={t("detailLocationLabel")}>
        <h3>{t("detailLocationLabel")}</h3>
        <p>
          <strong>{detail.location.display_name}</strong>
          {detail.location.display_address !== detail.location.display_name ? (
            <>
              <br />
              {detail.location.display_address}
            </>
          ) : null}
        </p>
        {detail.location.confidence === "low" ? (
          <p className="confidence-note">{t("lowConfidence")}</p>
        ) : null}
      </section>

      {detail.development ? (
        <section aria-label={t("detailDevelopmentLabel")}>
          <h3>{t("detailDevelopmentLabel")}</h3>
          <p>{detail.development.display_name}</p>
        </section>
      ) : null}

      {detail.field_confidence.length > 0 ? (
        <section aria-label={t("detailConfidenceLabel")}>
          <h3>{t("detailConfidenceLabel")}</h3>
          <ul className="offer-detail-confidence">
            {detail.field_confidence.map((entry) => {
              const labelKey = detailFieldLabelKeys[entry.field];
              return (
                <li key={entry.field}>
                  <span>{labelKey ? t(labelKey) : entry.field}</span>
                  <span>{t(`detailConfidence.${entry.confidence}`)}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <section aria-label={t("detailSourceTextLabel")}>
        <h3>{t("detailSourceTextLabel")}</h3>
        <p className="offer-detail-source-text">{detail.public_source_text}</p>
      </section>

      <ContactRevealSection
        key={`${detail.id}:${account?.id ?? "anon"}`}
        offerId={detail.id}
        account={account}
        onRequestSignIn={onRequestSignIn}
        onRequestPasswordChange={onRequestPasswordChange}
      />

      {detail.source_history.length > 0 ? (
        <section aria-label={t("detailSourceHistoryLabel")}>
          <h3>{t("detailSourceHistoryLabel")}</h3>
          <ol className="offer-detail-history">
            {detail.source_history.map((entry) => (
              <li key={entry.source_message_id}>
                <strong>{entry.relationship}</strong>
                <time dateTime={entry.published_at}>
                  {formatPublishedDate(entry.published_at)}
                </time>
                {entry.edited_at ? (
                  <span>
                    {t("detailEditedAt", {
                      date: formatPublishedDate(entry.edited_at),
                    })}
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section aria-label={t("detailMediaLabel")}>
        <h3>{t("detailMediaLabel")}</h3>
        <OfferMediaGallery detail={detail} media={detail.media} />
      </section>

      <section aria-label={t("detailSourceActionLabel")}>
        {verifiedLink ? (
          <a
            className="offer-detail-telegram-link"
            href={verifiedLink}
            rel="noopener noreferrer"
            target="_blank"
          >
            {t("detailOpenTelegram")}
          </a>
        ) : (
          <p className="offer-detail-source-fallback">
            {detail.source_message_id
              ? t("detailSourceFallbackWithId", {
                  id: detail.source_message_id,
                  date: formatPublishedDate(detail.published_at),
                })
              : t("detailSourceFallback", {
                  date: formatPublishedDate(detail.published_at),
                })}
          </p>
        )}
      </section>
    </div>
  );
}

type DetailRowProps = {
  label: string;
  value: string | null;
};

function DetailRow({ label, value }: DetailRowProps) {
  if (value === null || value.trim() === "") return null;
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
