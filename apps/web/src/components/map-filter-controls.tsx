"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState, type ReactNode } from "react";

import type { FilterFacets } from "@/lib/catalog-api";
import {
  DEFAULT_CONTENT_TYPES,
  type ContentType,
  type MapSearchState,
  type MarketType,
} from "@/lib/map-search-params";

type MapFilterControlsProps = {
  facets: FilterFacets | null;
  facetsError: boolean;
  facetsLoading: boolean;
  state: MapSearchState;
  onApply: (state: MapSearchState) => void;
  onClear: () => void;
};

export function MapFilterControls({
  facets,
  facetsError,
  facetsLoading,
  state,
  onApply,
  onClear,
}: MapFilterControlsProps) {
  const t = useTranslations("map");
  const [draft, setDraft] = useState(state);

  const districtOptions = useMemo(
    () => mergeOptions(facets?.districts ?? [], draft.districts),
    [draft.districts, facets?.districts],
  );
  const roomOptions = useMemo(
    () => mergeOptions(facets?.rooms ?? [], draft.rooms),
    [draft.rooms, facets?.rooms],
  );
  const marketOptions = useMemo(
    () =>
      mergeOptions<MarketType>(
        facets?.market_types ?? ["primary", "secondary"],
        draft.marketTypes,
      ),
    [draft.marketTypes, facets?.market_types],
  );
  const contentOptions = useMemo(
    () =>
      mergeOptions<ContentType>(
        facets?.content_types ?? DEFAULT_CONTENT_TYPES,
        draft.contentTypes,
      ),
    [draft.contentTypes, facets?.content_types],
  );

  return (
    <form
      className="filter-panel"
      aria-labelledby="filter-panel-title"
      onSubmit={(event) => {
        event.preventDefault();
        onApply(draft);
      }}
    >
      <div className="filter-heading">
        <div>
          <p className="eyebrow">{t("filtersEyebrow")}</p>
          <h2 id="filter-panel-title">{t("filtersTitle")}</h2>
        </div>
        <div className="filter-actions">
          <button className="button-secondary" type="button" onClick={onClear}>
            {t("clearFilters")}
          </button>
          <button className="button-primary" type="submit">
            {t("applyFilters")}
          </button>
        </div>
      </div>

      <div className="filter-grid">
        <FilterRange label={t("priceLabel")}>
          <label>
            <span>{t("minimumPrice")}</span>
            <input
              type="number"
              inputMode="numeric"
              min={minorToPln(facets?.price_min_minor ?? null) ?? undefined}
              max={minorToPln(facets?.price_max_minor ?? null) ?? undefined}
              step="any"
              value={minorToPln(draft.priceMinMinor) ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  priceMinMinor: plnToMinor(event.target.value),
                }))
              }
            />
          </label>
          <label>
            <span>{t("maximumPrice")}</span>
            <input
              type="number"
              inputMode="numeric"
              min={minorToPln(facets?.price_min_minor ?? null) ?? undefined}
              max={minorToPln(facets?.price_max_minor ?? null) ?? undefined}
              step="any"
              value={minorToPln(draft.priceMaxMinor) ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  priceMaxMinor: plnToMinor(event.target.value),
                }))
              }
            />
          </label>
        </FilterRange>

        <FilterRange label={t("areaLabel")}>
          <label>
            <span>{t("minimumArea")}</span>
            <input
              type="number"
              inputMode="decimal"
              min={facets?.area_min_sqm ?? undefined}
              max={facets?.area_max_sqm ?? undefined}
              step="any"
              value={draft.areaMin ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  areaMin: emptyToNull(event.target.value),
                }))
              }
            />
          </label>
          <label>
            <span>{t("maximumArea")}</span>
            <input
              type="number"
              inputMode="decimal"
              min={facets?.area_min_sqm ?? undefined}
              max={facets?.area_max_sqm ?? undefined}
              step="any"
              value={draft.areaMax ?? ""}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  areaMax: emptyToNull(event.target.value),
                }))
              }
            />
          </label>
        </FilterRange>

        <CheckboxGroup legend={t("roomsLabel")}>
          {roomOptions.map((room) => (
            <Checkbox
              key={room}
              checked={draft.rooms.includes(room)}
              label={t("roomOption", { room })}
              onChange={() =>
                setDraft((current) => ({
                  ...current,
                  rooms: toggleValue(current.rooms, room),
                }))
              }
            />
          ))}
        </CheckboxGroup>

        <CheckboxGroup legend={t("districtsLabel")}>
          {districtOptions.map((district) => (
            <Checkbox
              key={district}
              checked={draft.districts.includes(district)}
              label={formatOption(district)}
              onChange={() =>
                setDraft((current) => ({
                  ...current,
                  districts: toggleValue(current.districts, district),
                }))
              }
            />
          ))}
        </CheckboxGroup>

        <CheckboxGroup legend={t("marketTypeLabel")}>
          {marketOptions.map((marketType) => (
            <Checkbox
              key={marketType}
              checked={draft.marketTypes.includes(marketType)}
              label={t(`marketType.${marketType}`)}
              onChange={() =>
                setDraft((current) => ({
                  ...current,
                  marketTypes: toggleValue(current.marketTypes, marketType),
                }))
              }
            />
          ))}
        </CheckboxGroup>

        <CheckboxGroup legend={t("contentTypeLabel")}>
          {contentOptions.map((contentType) => (
            <Checkbox
              key={contentType}
              checked={draft.contentTypes.includes(contentType)}
              label={t(`contentType.${contentType}`)}
              onChange={() =>
                setDraft((current) => {
                  const next = toggleValue(current.contentTypes, contentType);
                  return {
                    ...current,
                    contentTypes:
                      next.length === 0 ? current.contentTypes : next,
                  };
                })
              }
            />
          ))}
        </CheckboxGroup>

        <FilterRange label={t("publicationLabel")}>
          <label>
            <span>{t("publishedFrom")}</span>
            <input
              type="date"
              min={dateInputValue(facets?.published_from ?? null) || undefined}
              max={dateInputValue(facets?.published_to ?? null) || undefined}
              value={dateInputValue(draft.publishedFrom)}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  publishedFrom: dateTimeValue(event.target.value, false),
                }))
              }
            />
          </label>
          <label>
            <span>{t("publishedTo")}</span>
            <input
              type="date"
              min={dateInputValue(facets?.published_from ?? null) || undefined}
              max={dateInputValue(facets?.published_to ?? null) || undefined}
              value={dateInputValue(draft.publishedTo)}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  publishedTo: dateTimeValue(event.target.value, true),
                }))
              }
            />
          </label>
        </FilterRange>
      </div>

      {facetsLoading ? (
        <p className="filter-status" role="status">
          {t("facetsLoading")}
        </p>
      ) : null}
      {facetsError ? (
        <p className="filter-status state-error" role="alert">
          {t("facetsError")}
        </p>
      ) : null}
    </form>
  );
}

type FilterRangeProps = {
  children: ReactNode;
  label: string;
};

function FilterRange({ children, label }: FilterRangeProps) {
  return (
    <fieldset className="filter-group filter-range">
      <legend>{label}</legend>
      <div>{children}</div>
    </fieldset>
  );
}

type CheckboxGroupProps = {
  children: ReactNode;
  legend: string;
};

function CheckboxGroup({ children, legend }: CheckboxGroupProps) {
  return (
    <fieldset className="filter-group filter-checkboxes">
      <legend>{legend}</legend>
      <div>{children}</div>
    </fieldset>
  );
}

type CheckboxProps = {
  checked: boolean;
  label: string;
  onChange: () => void;
};

function Checkbox({ checked, label, onChange }: CheckboxProps) {
  return (
    <label>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span>{label}</span>
    </label>
  );
}

function mergeOptions<T extends number | string>(first: T[], second: T[]) {
  return [...new Set([...first, ...second])].sort((left, right) =>
    typeof left === "number" && typeof right === "number"
      ? left - right
      : String(left).localeCompare(String(right)),
  );
}

function toggleValue<T>(values: T[], value: T) {
  return values.includes(value)
    ? values.filter((candidate) => candidate !== value)
    : [...values, value];
}

function minorToPln(value: number | null) {
  return value === null ? null : value / 100;
}

function plnToMinor(value: string) {
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed * 100) : null;
}

function emptyToNull(value: string) {
  return value === "" ? null : value;
}

function dateInputValue(value: string | null) {
  return value?.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? "";
}

function dateTimeValue(value: string, endOfDay: boolean) {
  if (value === "") return null;
  return `${value}T${endOfDay ? "23:59:59.999" : "00:00:00.000"}Z`;
}

function formatOption(value: string) {
  return value
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
