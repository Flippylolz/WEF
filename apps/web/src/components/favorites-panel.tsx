"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import type { FavoriteLocation } from "@/lib/favorites-api";

type FavoritesPanelProps = {
  open: boolean;
  items: FavoriteLocation[];
  loading: boolean;
  onClose: () => void;
  onSelect: (locationId: string) => void;
  onRemove: (locationId: string) => Promise<boolean>;
};

export function FavoritesPanel({
  open,
  items,
  loading,
  onClose,
  onSelect,
  onRemove,
}: FavoritesPanelProps) {
  const t = useTranslations("favorites");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="account-modal favorites-panel"
      aria-labelledby="favorites-panel-title"
      onCancel={(event) => {
        event.preventDefault();
        setPendingId(null);
        setRemoveError(false);
        onClose();
      }}
      onClose={() => {
        setPendingId(null);
        setRemoveError(false);
        onClose();
      }}
    >
      <div className="account-modal-panel">
        <header className="account-modal-header">
          <div>
            <p className="eyebrow">{t("eyebrow")}</p>
            <h2 id="favorites-panel-title">{t("title")}</h2>
          </div>
          <button
            className="account-modal-close"
            type="button"
            aria-label={t("close")}
            onClick={onClose}
          >
            ×
          </button>
        </header>
        {loading ? (
          <p role="status">{t("loading")}</p>
        ) : items.length === 0 ? (
          <p role="status">{t("empty")}</p>
        ) : (
          <ul className="favorites-list">
            {items.map((item) => (
              <li key={item.location_id}>
                <div className="location-button-row">
                  <button
                    className="location-button"
                    type="button"
                    onClick={() => {
                      onSelect(item.location_id);
                      onClose();
                    }}
                  >
                    <span>
                      <strong>{item.display_name}</strong>
                      <small>{item.display_address}</small>
                    </span>
                  </button>
                  <button
                    className="location-star-button location-star-button-active"
                    type="button"
                    aria-label={t("remove", { name: item.display_name })}
                    aria-pressed="true"
                    disabled={pendingId === item.location_id}
                    onClick={() => {
                      void (async () => {
                        setRemoveError(false);
                        setPendingId(item.location_id);
                        const removed = await onRemove(item.location_id);
                        setPendingId(null);
                        if (!removed) setRemoveError(true);
                      })();
                    }}
                  >
                    ★
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {removeError ? (
          <p className="account-modal-notice" role="alert">
            {t("removeFailed")}
          </p>
        ) : null}
      </div>
    </dialog>
  );
}
