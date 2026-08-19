"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import type { FavoriteLocation } from "@/lib/favorites-api";

type FavoritesPanelProps = {
  open: boolean;
  items: FavoriteLocation[];
  loading: boolean;
  onClose: () => void;
  onSelect: (locationId: string) => void;
};

export function FavoritesPanel({
  open,
  items,
  loading,
  onClose,
  onSelect,
}: FavoritesPanelProps) {
  const t = useTranslations("favorites");
  const dialogRef = useRef<HTMLDialogElement>(null);

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
        onClose();
      }}
      onClose={onClose}
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
              </li>
            ))}
          </ul>
        )}
      </div>
    </dialog>
  );
}
