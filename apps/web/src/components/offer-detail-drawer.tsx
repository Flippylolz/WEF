"use client";
import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef } from "react";
import type { Account } from "@/lib/auth-api";
import type { OfferDetail } from "@/lib/catalog-api";
import { OfferDetailContent } from "@/components/offer-detail/offer-detail-content";

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
        aria-hidden="true"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
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
      </div>
    </div>
  );
}
