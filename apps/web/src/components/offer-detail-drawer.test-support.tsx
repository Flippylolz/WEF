import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { cleanup, render } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { OfferDetailDrawer } from "@/components/offer-detail-drawer";
import type { Account } from "@/lib/auth-api";
import type { OfferDetail } from "@/lib/catalog-api";
import * as catalogApi from "@/lib/catalog-api";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: Record<string, string | number>) => {
      if (values) {
        return `${key}:${JSON.stringify(values)}`;
      }
      return key;
    },
}));

vi.mock("@/lib/contacts-api", () => ({
  revealOfferContacts: vi.fn(),
}));

export const detail: OfferDetail = {
  id: "20000000-0000-4000-8000-000000000001",
  content_type: "development",
  market_type: "primary",
  property_type: "unknown",
  display_name: "development · primary",
  data_confidence: "complete",
  data_origin: "parser",
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
    id: "10000000-0000-4000-8000-000000000001",
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
  media: [
    {
      media_asset_id: "40000000-0000-4000-8000-000000000001",
      position: 0,
      media_type: "image",
      mime_type: "image/jpeg",
      thumbnail_url: "/media/thumb.jpg",
      content_url: "/media/full.jpg",
    },
  ],
  source_message_id: "50000000-0000-4000-8000-000000000001",
  verified_source_url: "https://t.me/elestate_warszawa/42",
  source_history: [
    {
      source_message_id: "50000000-0000-4000-8000-000000000001",
      relationship: "original",
      published_at: "2026-08-01T10:00:00Z",
      edited_at: null,
    },
  ],
};

export const signedInAccount: Account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user",
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

export class OfferNotFoundError extends Error {
  override name = "OfferNotFoundError";
}

export function DrawerHarness({
  offerId,
  matchesFilters = true,
  account = null,
  onClose = () => undefined,
  onRequestSignIn = () => undefined,
  onRequestPasswordChange = () => undefined,
}: {
  offerId: string;
  matchesFilters?: boolean;
  account?: Account | null;
  onClose?: () => void;
  onRequestSignIn?: () => void;
  onRequestPasswordChange?: () => void;
}) {
  const returnFocusRef = { current: document.createElement("button") };
  const detailQuery = useQuery({
    queryKey: ["offer-detail", offerId],
    queryFn: async ({ signal }) => {
      const result = await catalogApi.fetchOfferDetail(offerId, { signal });
      if (result.state === "not_found") throw new OfferNotFoundError();
      if (result.state === "error") throw new Error("offer-detail");
      return result.data;
    },
  });

  return (
    <OfferDetailDrawer
      open
      offerId={offerId}
      matchesFilters={matchesFilters}
      detailQuery={detailQuery}
      account={account}
      onClose={onClose}
      onRequestSignIn={onRequestSignIn}
      onRequestPasswordChange={onRequestPasswordChange}
      returnFocusRef={returnFocusRef}
    />
  );
}

export function renderDrawer(
  offerId = detail.id,
  options: {
    account?: Account | null;
    onRequestSignIn?: () => void;
    onRequestPasswordChange?: () => void;
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DrawerHarness offerId={offerId} {...options} />
    </QueryClientProvider>,
  );
}

export function setupOfferDetailDrawer() {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });
}
