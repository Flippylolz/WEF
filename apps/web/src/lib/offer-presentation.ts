import type { OfferDetail } from "@/lib/catalog-api";

export function formatPrice(min: number | null, max: number | null) {
  if (min === null || max === null) return null;
  const formatter = new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  });
  return min === max
    ? formatter.format(min / 100)
    : `${formatter.format(min / 100)}–${formatter.format(max / 100)}`;
}

export function formatAdditionalPrice(
  min: number | null,
  max: number | null,
  included: boolean,
  includedLabel: string,
) {
  if (included) return includedLabel;
  if (min === null || max === null) return null;
  return formatPrice(min, max);
}

export function formatArea(min: string | null, max: string | null) {
  if (min === null || max === null) return null;
  return min === max ? `${min} m²` : `${min}–${max} m²`;
}

export function formatRooms(min: number | null, max: number | null) {
  if (min === null || max === null) return null;
  return min === max ? String(min) : `${min}–${max}`;
}

export function formatPublishedDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function isSafeExternalUrl(value: string | null | undefined) {
  if (value === null || value === undefined || value.trim() === "")
    return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function mediaAltText(
  detail: Pick<OfferDetail, "display_name" | "location">,
  index: number,
  total: number,
) {
  return `${detail.display_name} at ${detail.location.display_name}, media ${index + 1} of ${total}`;
}

export function pickMediaDisplayUrl(
  thumbnailUrl: string | null,
  contentUrl: string | null,
) {
  return contentUrl ?? thumbnailUrl;
}
