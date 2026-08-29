import type { components, operations } from "@/generated/api";

export type ContentType = components["schemas"]["ContentType"];
export type MarketType = components["schemas"]["MarketType"];
export type MapLocationQuery =
  operations["queryMapLocations"]["parameters"]["query"];

export const DEFAULT_BBOX = "20.7,52.0,21.4,52.4";
export const DEFAULT_CONTENT_TYPES: ContentType[] = ["development", "unit"];
const WARSAW_LONGITUDE_RANGE = [20.5, 21.6] as const;
const WARSAW_LATITUDE_RANGE = [51.8, 52.6] as const;
// The backend rejects spans above 0.8 measured on floats re-parsed from the
// six-decimal bbox string, where an exact 0.8 span can round-trip as
// 0.8000000000000007. Keep a margin so every emitted bbox stays queryable.
const MAX_BBOX_SPAN = 0.799;

export type MapSearchState = {
  bbox: string;
  priceMinMinor: number | null;
  priceMaxMinor: number | null;
  areaMin: string | null;
  areaMax: string | null;
  rooms: number[];
  districts: string[];
  marketTypes: MarketType[];
  contentTypes: ContentType[];
  publishedFrom: string | null;
  publishedTo: string | null;
  quickFilter: string | null;
};

export const DEFAULT_MAP_SEARCH_STATE: MapSearchState = {
  bbox: DEFAULT_BBOX,
  priceMinMinor: null,
  priceMaxMinor: null,
  areaMin: null,
  areaMax: null,
  rooms: [],
  districts: [],
  marketTypes: [],
  contentTypes: DEFAULT_CONTENT_TYPES,
  publishedFrom: null,
  publishedTo: null,
  quickFilter: null,
};

const MARKET_TYPES = new Set<MarketType>(["primary", "secondary", "unknown"]);
const CONTENT_TYPES = new Set<ContentType>(["development", "unit"]);

export function parseMapSearchParams(
  searchParams: Pick<URLSearchParams, "get" | "getAll">,
): MapSearchState {
  const parsedContentTypes = uniqueSorted(
    searchParams
      .getAll("content_type")
      .filter((value): value is ContentType =>
        CONTENT_TYPES.has(value as ContentType),
      ),
  );

  return {
    bbox: normalizeBbox(searchParams.get("bbox")) ?? DEFAULT_BBOX,
    priceMinMinor: parseInteger(searchParams.get("price_min")),
    priceMaxMinor: parseInteger(searchParams.get("price_max")),
    areaMin: parseDecimal(searchParams.get("area_min")),
    areaMax: parseDecimal(searchParams.get("area_max")),
    rooms: uniqueSorted(
      searchParams
        .getAll("rooms")
        .map(parseInteger)
        .filter((value): value is number => value !== null),
    ),
    districts: uniqueSorted(
      searchParams
        .getAll("district")
        .map((value) => value.trim())
        .filter(Boolean),
    ),
    marketTypes: uniqueSorted(
      searchParams
        .getAll("market_type")
        .filter((value): value is MarketType =>
          MARKET_TYPES.has(value as MarketType),
        ),
    ),
    contentTypes:
      parsedContentTypes.length === 0
        ? [...DEFAULT_CONTENT_TYPES]
        : parsedContentTypes,
    publishedFrom: parseTimestamp(searchParams.get("published_from"), false),
    publishedTo: parseTimestamp(searchParams.get("published_to"), true),
    quickFilter: parseQuickFilter(searchParams.get("quick_filter")),
  };
}

function parseQuickFilter(value: string | null) {
  const parsed = value?.trim();
  return parsed ? parsed : null;
}

export function serializeMapSearchState(state: MapSearchState) {
  const params = new URLSearchParams();

  if (state.bbox !== DEFAULT_BBOX) params.set("bbox", state.bbox);
  appendNumber(params, "price_min", state.priceMinMinor);
  appendNumber(params, "price_max", state.priceMaxMinor);
  appendText(params, "area_min", state.areaMin);
  appendText(params, "area_max", state.areaMax);
  appendRepeated(params, "rooms", state.rooms);
  appendRepeated(params, "district", state.districts);
  appendRepeated(params, "market_type", state.marketTypes);
  if (!hasBothContentTypes(state.contentTypes)) {
    appendRepeated(params, "content_type", state.contentTypes);
  }
  appendText(params, "published_from", state.publishedFrom);
  appendText(params, "published_to", state.publishedTo);
  appendText(params, "quick_filter", state.quickFilter);

  return params.toString();
}

export function toMapLocationQuery(state: MapSearchState): MapLocationQuery {
  return {
    bbox: state.bbox,
    ...(state.priceMinMinor === null ? {} : { price_min: state.priceMinMinor }),
    ...(state.priceMaxMinor === null ? {} : { price_max: state.priceMaxMinor }),
    ...(state.areaMin === null ? {} : { area_min: state.areaMin }),
    ...(state.areaMax === null ? {} : { area_max: state.areaMax }),
    ...(state.rooms.length === 0 ? {} : { rooms: state.rooms }),
    ...(state.districts.length === 0 ? {} : { district: state.districts }),
    ...(state.marketTypes.length === 0
      ? {}
      : { market_type: state.marketTypes }),
    ...(hasBothContentTypes(state.contentTypes)
      ? {}
      : { content_type: state.contentTypes }),
    ...(state.publishedFrom === null
      ? {}
      : { published_from: state.publishedFrom }),
    ...(state.publishedTo === null ? {} : { published_to: state.publishedTo }),
    ...(state.quickFilter === null ? {} : { quick_filter: state.quickFilter }),
  };
}

export function normalizeBbox(value: string | null) {
  if (value === null) return null;
  const coordinates = parseBbox(value);
  if (coordinates === null) return null;
  if (sameBbox(coordinates, parseBbox(DEFAULT_BBOX)!)) return DEFAULT_BBOX;
  return formatBbox(coordinates);
}

export function parseBbox(
  value: string,
): [number, number, number, number] | null {
  const parts = value.split(",");
  if (parts.length !== 4) return null;
  const coordinates = parts.map((part) => Number(part.trim()));
  if (coordinates.some((coordinate) => !Number.isFinite(coordinate))) {
    return null;
  }
  return coordinates as [number, number, number, number];
}

export function formatBbox(
  coordinates: [number, number, number, number],
): string {
  return coordinates
    .map((coordinate) => String(Number(coordinate.toFixed(6))))
    .join(",");
}

export function boundedWarsawViewport(
  coordinates: [number, number, number, number],
) {
  const longitude = boundedRange(
    coordinates[0],
    coordinates[2],
    WARSAW_LONGITUDE_RANGE,
  );
  const latitude = boundedRange(
    coordinates[1],
    coordinates[3],
    WARSAW_LATITUDE_RANGE,
  );
  return formatBbox([longitude[0], latitude[0], longitude[1], latitude[1]]);
}

function parseInteger(value: string | null) {
  if (value === null || !/^-?\d+$/.test(value.trim())) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function parseDecimal(value: string | null) {
  if (value === null || !/^-?(?:\d+\.?\d*|\.\d+)$/.test(value.trim())) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? String(parsed) : null;
}

function parseText(value: string | null) {
  const parsed = value?.trim();
  return parsed ? parsed : null;
}

function parseTimestamp(value: string | null, endOfDay: boolean) {
  const parsed = parseText(value);
  if (parsed === null) return null;
  const dateOnly = parsed.match(/^\d{4}-\d{2}-\d{2}$/)?.[0];
  const candidate = dateOnly
    ? `${dateOnly}T${endOfDay ? "23:59:59.999" : "00:00:00.000"}Z`
    : parsed;
  const timestamp = candidate.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?(Z|[+-]\d{2}:\d{2})$/,
  );
  if (timestamp === null) {
    return null;
  }
  const [, year, month, day, hour, minute, second = "0"] = timestamp;
  if (
    !validCalendarDate(Number(year), Number(month), Number(day)) ||
    Number(hour) > 23 ||
    Number(minute) > 59 ||
    Number(second) > 59
  ) {
    return null;
  }
  const date = new Date(candidate);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function validCalendarDate(year: number, month: number, day: number) {
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function uniqueSorted<T extends number | string>(values: T[]) {
  // Code-unit ordering keeps URL state identical across runtimes and locales.
  return [...new Set(values)].sort((left, right) => {
    if (typeof left === "number" && typeof right === "number")
      return left - right;
    const l = String(left);
    const r = String(right);
    return l < r ? -1 : l > r ? 1 : 0;
  });
}

function appendNumber(
  params: URLSearchParams,
  name: string,
  value: number | null,
) {
  if (value !== null) params.set(name, String(value));
}

function appendText(
  params: URLSearchParams,
  name: string,
  value: string | null,
) {
  if (value !== null) params.set(name, value);
}

function appendRepeated(
  params: URLSearchParams,
  name: string,
  values: (number | string)[],
) {
  for (const value of uniqueSorted(values)) params.append(name, String(value));
}

function hasBothContentTypes(values: ContentType[]) {
  return (
    values.length === DEFAULT_CONTENT_TYPES.length &&
    DEFAULT_CONTENT_TYPES.every((value) => values.includes(value))
  );
}

function sameBbox(
  left: [number, number, number, number],
  right: [number, number, number, number],
) {
  return left.every((value, index) => value === right[index]);
}

function boundedRange(
  first: number,
  second: number,
  boundary: readonly [number, number],
): [number, number] {
  const lower = Math.min(
    boundary[1],
    Math.max(boundary[0], Math.min(first, second)),
  );
  const upper = Math.max(
    boundary[0],
    Math.min(boundary[1], Math.max(first, second)),
  );
  const span = Math.min(Math.max(upper - lower, 0), MAX_BBOX_SPAN);
  const center = Math.min(
    boundary[1] - span / 2,
    Math.max(boundary[0] + span / 2, (lower + upper) / 2),
  );
  return [center - span / 2, center + span / 2];
}
