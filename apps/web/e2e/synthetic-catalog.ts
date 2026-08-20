/** Synthetic M1 fixtures for Playwright critical-path mocks (no personal data). */

export const LOCATION_ID = "10000000-0000-4000-8000-000000000001";
export const OFFER_ID = "20000000-0000-4000-8000-000000000001";
export const OFFER_ID_NO_LINK = "20000000-0000-4000-8000-000000000002";

export const mapLocations = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: LOCATION_ID,
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
      properties: {
        display_name: "Synthetic Central Residence",
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "low",
        matching_offer_count: 1,
        total_offer_count: 2,
        latest_published_at: "2026-08-01T10:00:00Z",
        price_min_minor: 80_000_000,
        price_max_minor: 125_000_000,
        area_min_sqm: "35.00",
        area_max_sqm: "71.50",
        currency: "PLN",
      },
    },
  ],
  meta: {
    request_id: "00000000-0000-4000-8000-000000000001",
    feature_count: 1,
    matching_offer_count: 1,
  },
};

export const filterFacets = {
  districts: ["srodmiescie"],
  rooms: [1, 2, 3],
  market_types: ["primary"],
  content_types: ["development"],
  price_min_minor: 80_000_000,
  price_max_minor: 125_000_000,
  area_min_sqm: "35.00",
  area_max_sqm: "71.50",
  published_from: "2026-08-01T10:00:00Z",
  published_to: "2026-08-01T10:00:00Z",
};

export const quickFilters = {
  items: [{ id: "last_day", label_key: "quickFilter.last_day" }],
};

export const locationOffers = {
  items: [
    {
      id: OFFER_ID,
      content_type: "development",
      market_type: "primary",
      display_name: "development · primary",
      data_confidence: "complete",
      published_at: "2026-08-01T10:00:00Z",
      currency: "PLN",
      price_min_minor: 80_000_000,
      price_max_minor: 125_000_000,
      parking_price_min_minor: 4_500_000,
      parking_price_max_minor: 4_500_000,
      parking_included_in_price: false,
      storage_price_min_minor: null,
      storage_price_max_minor: null,
      storage_included_in_price: true,
      area_min_sqm: "35.00",
      area_max_sqm: "71.50",
      rooms_min: 1,
      rooms_max: 3,
      floor_label: null,
      delivery_label: "Synthetic delivery",
      matches_filters: true,
    },
    {
      id: OFFER_ID_NO_LINK,
      content_type: "secondary",
      market_type: "secondary",
      display_name: "secondary · no verified link",
      data_confidence: "partial",
      published_at: "2026-07-15T10:00:00Z",
      currency: "PLN",
      price_min_minor: 90_000_000,
      price_max_minor: 90_000_000,
      parking_price_min_minor: null,
      parking_price_max_minor: null,
      parking_included_in_price: null,
      storage_price_min_minor: null,
      storage_price_max_minor: null,
      storage_included_in_price: null,
      area_min_sqm: "40.00",
      area_max_sqm: "40.00",
      rooms_min: 2,
      rooms_max: 2,
      floor_label: null,
      delivery_label: null,
      matches_filters: true,
    },
  ],
  matching_count: 2,
  total_count: 2,
  next_cursor: null,
};

function offerDetailBase(id: string, verifiedSourceUrl: string | null) {
  return {
    id,
    content_type: "development",
    market_type: "primary",
    display_name:
      id === OFFER_ID_NO_LINK
        ? "secondary · no verified link"
        : "development · primary",
    data_confidence: "complete",
    published_at: "2026-08-01T10:00:00Z",
    currency: "PLN",
    price_min_minor: 80_000_000,
    price_max_minor: 125_000_000,
    parking_price_min_minor: 4_500_000,
    parking_price_max_minor: 4_500_000,
    parking_included_in_price: false,
    storage_price_min_minor: null,
    storage_price_max_minor: null,
    storage_included_in_price: true,
    area_min_sqm: "35.00",
    area_max_sqm: "71.50",
    rooms_min: 1,
    rooms_max: 3,
    floor_label: null,
    delivery_label: "Synthetic delivery",
    public_source_text: "Masked public text only.",
    parser_version: "synthetic-m1-v1",
    location: {
      id: LOCATION_ID,
      display_name: "Synthetic Central Residence",
      display_address: "Synthetic address, Warsaw",
      district: "srodmiescie",
      coordinate_precision: "district",
      confidence: "low",
    },
    development: {
      id: "30000000-0000-4000-8000-000000000001",
      display_name: "Synthetic Project",
      name_confidence: "medium",
    },
    field_confidence: [{ field: "area_sqm", confidence: "high" }],
    media: [],
    source_message_id: "50000000-0000-4000-8000-000000000001",
    verified_source_url: verifiedSourceUrl,
    source_observed_at: "2026-08-01T10:00:00Z",
    source_channel_username: null,
    publication_disclaimer:
      "Public historical inventory is illustrative; availability is not claimed.",
    source_history: [
      {
        source_message_id: "50000000-0000-4000-8000-000000000001",
        relationship: "original",
        published_at: "2026-08-01T10:00:00Z",
        edited_at: null,
      },
    ],
  };
}

export const offerDetailVerified = offerDetailBase(
  OFFER_ID,
  "https://t.me/elestate_warszawa/42",
);

export const offerDetailMissingLink = offerDetailBase(OFFER_ID_NO_LINK, null);
