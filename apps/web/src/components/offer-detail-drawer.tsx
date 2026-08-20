"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { OfferMediaGallery } from "@/components/offer-media-gallery";
import type { Account } from "@/lib/auth-api";
import type { OfferDetail } from "@/lib/catalog-api";
import { revealOfferContacts, type RevealedContact } from "@/lib/contacts-api";
import {
  formatAdditionalPrice,
  formatArea,
  formatPrice,
  formatPublishedDate,
  formatRooms,
  isSafeExternalUrl,
} from "@/lib/offer-presentation";

export type OfferDetailDrawerProps = {
  open: boolean;
  offerId: string | null;
  matchesFilters: boolean | null;
  detailQuery: UseQueryResult<OfferDetail, Error>;
  account: Account | null | undefined;
  onClose: () => void;
  onRetry?: () => void;
  onRequestSignIn: () => void;
  onRequestPasswordChange: () => void;
  returnFocusRef: React.RefObject<HTMLButtonElement | null>;
};

export function OfferDetailDrawer({
  open,
  offerId,
  matchesFilters,
  detailQuery,
  account,
  onClose,
  onRetry,
  onRequestSignIn,
  onRequestPasswordChange,
  returnFocusRef,
}: OfferDetailDrawerProps) {
  const t = useTranslations("map");
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (open) {
      closeButtonRef.current?.focus();
      wasOpen.current = true;
      return;
    }
    if (wasOpen.current) {
      returnFocusRef.current?.focus();
      wasOpen.current = false;
    }
  }, [open, returnFocusRef]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open || offerId === null) return null;

  const detail = detailQuery.data;
  const showStaleDetail = detail !== undefined && detail.id !== offerId;

  return (
    <div className="offer-detail-overlay" data-testid="offer-detail-overlay">
      <button
        className="offer-detail-scrim"
        type="button"
        aria-label={t("detailClose")}
        onClick={onClose}
      />
      <aside
        className="offer-detail-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="offer-detail-header">
          <div>
            <p className="eyebrow">{t("detailEyebrow")}</p>
            <h2 id={titleId}>
              {detail && !showStaleDetail
                ? detail.display_name
                : t("detailLoadingTitle")}
            </h2>
          </div>
          <button ref={closeButtonRef} type="button" onClick={onClose}>
            {t("detailClose")}
          </button>
        </header>

        {detailQuery.isPending || showStaleDetail ? (
          <p className="offer-detail-status" role="status">
            {t("detailLoading")}
          </p>
        ) : null}

        {detailQuery.isError ? (
          <div className="offer-detail-status state-error" role="alert">
            <p>
              {detailQuery.error?.name === "OfferNotFoundError"
                ? t("detailNotFound")
                : t("detailError")}
            </p>
            {onRetry ? (
              <button type="button" onClick={onRetry}>
                {t("retry")}
              </button>
            ) : null}
          </div>
        ) : null}

        {detailQuery.isSuccess && detail && !showStaleDetail ? (
          <OfferDetailContent
            detail={detail}
            matchesFilters={matchesFilters}
            account={account}
            onRequestSignIn={onRequestSignIn}
            onRequestPasswordChange={onRequestPasswordChange}
          />
        ) : null}
      </aside>
    </div>
  );
}

type OfferDetailContentProps = {
  detail: OfferDetail;
  matchesFilters: boolean | null;
  account: Account | null | undefined;
  onRequestSignIn: () => void;
  onRequestPasswordChange: () => void;
};

function OfferDetailContent({
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

      <section aria-label={t("detailLocationLabel")}>
        <h3>{t("detailLocationLabel")}</h3>
        <p>
          <strong>{detail.location.display_name}</strong>
          <br />
          {detail.location.display_address}
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
            {detail.field_confidence.map((entry) => (
              <li key={entry.field}>
                <span>{entry.field}</span>
                <span>{t(`detailConfidence.${entry.confidence}`)}</span>
              </li>
            ))}
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

type ContactRevealSectionProps = {
  offerId: string;
  account: Account | null | undefined;
  onRequestSignIn: () => void;
  onRequestPasswordChange: () => void;
};

function ContactRevealSection({
  offerId,
  account,
  onRequestSignIn,
  onRequestPasswordChange,
}: ContactRevealSectionProps) {
  const t = useTranslations("map");
  const [contacts, setContacts] = useState<RevealedContact[] | null>(null);
  const [errorCode, setErrorCode] = useState<
    | "unauthorized"
    | "forbidden"
    | "not_found"
    | "rate_limited"
    | "unavailable"
    | "unknown"
    | null
  >(null);
  const [loading, setLoading] = useState(false);

  const signedIn = account != null;
  const mustChange = Boolean(account?.must_change_password);

  return (
    <section
      className="offer-detail-contacts"
      aria-label={t("detailContactsLabel")}
    >
      <h3>{t("detailContactsLabel")}</h3>
      {!signedIn ? (
        <>
          <p>{t("detailRevealSignInRequired")}</p>
          <button
            className="button-primary"
            type="button"
            onClick={onRequestSignIn}
          >
            {t("detailRevealSignInAction")}
          </button>
        </>
      ) : mustChange ? (
        <>
          <p>{t("detailRevealPasswordRequired")}</p>
          <button
            className="button-primary"
            type="button"
            onClick={onRequestPasswordChange}
          >
            {t("detailRevealPasswordAction")}
          </button>
        </>
      ) : contacts !== null ? (
        contacts.length === 0 ? (
          <p role="status">{t("detailRevealEmpty")}</p>
        ) : (
          <ul className="offer-detail-contact-list">
            {contacts.map((contact) => (
              <li key={`${contact.kind}:${contact.masked_value}`}>
                <span>{t(`detailRevealKind.${contact.kind}`)}</span>
                <strong>{contact.value}</strong>
              </li>
            ))}
          </ul>
        )
      ) : (
        <>
          <button
            className="button-primary"
            type="button"
            disabled={loading}
            onClick={async () => {
              setLoading(true);
              setErrorCode(null);
              const result = await revealOfferContacts(offerId);
              setLoading(false);
              if (result.state === "error") {
                setErrorCode(result.code ?? "unknown");
                return;
              }
              setContacts(result.data.contacts);
            }}
          >
            {loading ? t("detailRevealLoading") : t("detailRevealContacts")}
          </button>
          {errorCode ? (
            <p className="form-error" role="alert">
              {t(`detailRevealError.${errorCode}`)}
            </p>
          ) : null}
        </>
      )}
    </section>
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
