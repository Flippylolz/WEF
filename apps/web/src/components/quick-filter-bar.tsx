"use client";

import { useTranslations } from "next-intl";

type QuickFilterPreset = {
  id: string;
  label_key: string;
};

type QuickFilterBarProps = {
  presets: QuickFilterPreset[];
  selectedId: string | null;
  loading?: boolean;
  onSelect: (presetId: string | null) => void;
};

export function QuickFilterBar({
  presets,
  selectedId,
  loading = false,
  onSelect,
}: QuickFilterBarProps) {
  const t = useTranslations("map");

  if (loading) {
    return (
      <div className="quick-filter-bar" role="status">
        {t("quickFiltersLoading")}
      </div>
    );
  }

  if (presets.length === 0) return null;

  return (
    <div className="quick-filter-bar" aria-label={t("quickFiltersLabel")}>
      <p className="quick-filter-heading">{t("quickFiltersLabel")}</p>
      <div className="quick-filter-options">
        {presets.map((preset) => {
          const selected = selectedId === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              className={`quick-filter-chip${selected ? " quick-filter-chip-active" : ""}`}
              aria-pressed={selected}
              onClick={() => onSelect(selected ? null : preset.id)}
            >
              {t(preset.label_key)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
