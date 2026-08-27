"use client";

import { useTranslations } from "next-intl";

import type { QuickFilterPreset } from "@/lib/catalog-api";
import type { ContentType, MapSearchState } from "@/lib/map-search-params";

export type FilterChipGroup =
  | "price"
  | "area"
  | "rooms"
  | "districts"
  | "marketTypes"
  | "contentTypes"
  | "publication"
  | "quickFilter";

type AppliedFilterChipsProps = {
  state: MapSearchState;
  quickFilters: QuickFilterPreset[];
  quickFiltersLoading: boolean;
  lastVisitAt: string | null | undefined;
  onRemoveGroup: (group: FilterChipGroup) => void;
  onToggleQuickFilter: (presetId: string | null) => void;
  onToggleLastVisit: (publishedFrom: string | null) => void;
  onOpenFilters: () => void;
};

const pln = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "PLN",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
});

function formatMinor(minor: number) {
  return pln.format(minor / 100);
}

function formatPriceRange(state: MapSearchState) {
  if (state.priceMinMinor !== null && state.priceMaxMinor !== null) {
    return `${formatMinor(state.priceMinMinor)} – ${formatMinor(state.priceMaxMinor)}`;
  }
  if (state.priceMinMinor !== null) {
    return `≥ ${formatMinor(state.priceMinMinor)}`;
  }
  if (state.priceMaxMinor !== null) {
    return `≤ ${formatMinor(state.priceMaxMinor)}`;
  }
  return null;
}

function formatAreaRange(state: MapSearchState) {
  const min = state.areaMin === null ? null : Number(state.areaMin);
  const max = state.areaMax === null ? null : Number(state.areaMax);
  if (min !== null && max !== null) {
    return `${min} – ${max} m²`;
  }
  if (min !== null) {
    return `≥ ${min} m²`;
  }
  if (max !== null) {
    return `≤ ${max} m²`;
  }
  return null;
}

function formatPublication(
  state: MapSearchState,
  t: ReturnType<typeof useTranslations>,
) {
  const from =
    state.publishedFrom === null
      ? null
      : dateFormatter.format(new Date(state.publishedFrom));
  const to =
    state.publishedTo === null
      ? null
      : dateFormatter.format(new Date(state.publishedTo));
  if (from !== null && to !== null) {
    return t("chip.publicationRange", { from, to });
  }
  if (from !== null) {
    return t("chip.publicationFrom", { from });
  }
  if (to !== null) {
    return t("chip.publicationTo", { to });
  }
  return null;
}

export function countAppliedGroups(state: MapSearchState) {
  let count = 0;
  if (formatPriceRange(state) !== null) count += 1;
  if (formatAreaRange(state) !== null) count += 1;
  if (state.rooms.length > 0) count += 1;
  if (state.districts.length > 0) count += 1;
  if (state.marketTypes.length > 0) count += 1;
  if (!hasDefaultContentTypes(state.contentTypes)) count += 1;
  if (state.publishedFrom !== null || state.publishedTo !== null) count += 1;
  if (state.quickFilter !== null) count += 1;
  return count;
}

function hasDefaultContentTypes(values: ContentType[]) {
  return values.length === 0 || values.length === 2;
}

type AppliedChip = {
  group: FilterChipGroup;
  label: string;
  value: string;
};

function collectChips(
  state: MapSearchState,
  quickFilters: QuickFilterPreset[],
  t: ReturnType<typeof useTranslations>,
): AppliedChip[] {
  const chips: AppliedChip[] = [];

  const price = formatPriceRange(state);
  if (price !== null) {
    chips.push({ group: "price", label: t("priceLabel"), value: price });
  }

  const area = formatAreaRange(state);
  if (area !== null) {
    chips.push({ group: "area", label: t("areaLabel"), value: area });
  }

  if (state.rooms.length > 0) {
    chips.push({
      group: "rooms",
      label: t("roomsLabel"),
      value: t("chip.roomsValue", {
        rooms: state.rooms.join(", "),
        count: state.rooms.length,
      }),
    });
  }

  if (state.districts.length > 0) {
    const names = state.districts.map((district) =>
      district
        .replaceAll("-", " ")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase()),
    );
    chips.push({
      group: "districts",
      label: t("districtsLabel"),
      value:
        names.length <= 2
          ? names.join(", ")
          : t("chip.listValue", {
              values: names.slice(0, 2).join(", "),
              count: names.length,
            }),
    });
  }

  if (state.marketTypes.length > 0) {
    chips.push({
      group: "marketTypes",
      label: t("marketTypeLabel"),
      value: state.marketTypes
        .map((value) => t(`marketType.${value}`))
        .join(", "),
    });
  }

  if (!hasDefaultContentTypes(state.contentTypes)) {
    chips.push({
      group: "contentTypes",
      label: t("contentTypeLabel"),
      value: state.contentTypes
        .map((value) => t(`contentType.${value}`))
        .join(", "),
    });
  }

  const publication = formatPublication(state, t);
  if (publication !== null) {
    chips.push({
      group: "publication",
      label: t("publicationLabel"),
      value: publication,
    });
  }

  if (state.quickFilter !== null) {
    const preset = quickFilters.find((item) => item.id === state.quickFilter);
    if (preset) {
      chips.push({
        group: "quickFilter",
        label: t(preset.label_key),
        value: "",
      });
    }
  }

  return chips;
}

export function AppliedFilterChips({
  state,
  quickFilters,
  quickFiltersLoading,
  lastVisitAt,
  onRemoveGroup,
  onToggleQuickFilter,
  onToggleLastVisit,
  onOpenFilters,
}: AppliedFilterChipsProps) {
  const t = useTranslations("map");
  const lastVisitSelected =
    lastVisitAt !== null &&
    lastVisitAt !== undefined &&
    state.quickFilter === null &&
    state.publishedFrom === lastVisitAt;

  return (
    <div className="rail-controls">
      {quickFiltersLoading ? (
        <div className="quick-filter-bar" role="status">
          {t("quickFiltersLoading")}
        </div>
      ) : quickFilters.length > 0 || lastVisitAt !== undefined ? (
        <div className="quick-filter-bar" aria-label={t("quickFiltersLabel")}>
          {quickFilters.map((preset) => {
            const selected = state.quickFilter === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                className={`quick-filter-chip${selected ? " quick-filter-chip-active" : ""}`}
                aria-pressed={selected}
                onClick={() => onToggleQuickFilter(selected ? null : preset.id)}
              >
                {t(preset.label_key)}
              </button>
            );
          })}
          {lastVisitAt !== undefined ? (
            <button
              type="button"
              className={`quick-filter-chip${lastVisitSelected ? " quick-filter-chip-active" : ""}`}
              aria-label={
                lastVisitAt === null
                  ? `${t("quickFilter.since_last_visit")}. ${t("quickFilter.since_last_visit_unavailable")}`
                  : t("quickFilter.since_last_visit")
              }
              aria-pressed={lastVisitSelected}
              disabled={lastVisitAt === null}
              title={
                lastVisitAt === null
                  ? t("quickFilter.since_last_visit_unavailable")
                  : undefined
              }
              onClick={() =>
                onToggleLastVisit(lastVisitSelected ? null : lastVisitAt)
              }
            >
              {t("quickFilter.since_last_visit")}
            </button>
          ) : null}
        </div>
      ) : null}
      <div className="filter-chip-row">
        <button
          type="button"
          className="filter-chip"
          aria-haspopup="dialog"
          onClick={onOpenFilters}
        >
          {t("moreFilters")}
        </button>
        {collectChips(state, quickFilters, t).map((chip) => (
          <span key={chip.group} className="filter-chip filter-chip-applied">
            {chip.value ? (
              <>
                <span>{chip.label}</span>
                <span className="chip-value">{chip.value}</span>
              </>
            ) : (
              <span>{chip.label}</span>
            )}
            <button
              type="button"
              className="filter-chip-remove"
              aria-label={t("chipRemove", { label: chip.label })}
              onClick={() => {
                if (chip.group === "quickFilter") {
                  onToggleQuickFilter(null);
                } else {
                  onRemoveGroup(chip.group);
                }
              }}
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
