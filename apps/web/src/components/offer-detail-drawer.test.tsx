import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OfferDetailDrawer } from "@/components/offer-detail-drawer";
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

const detail: OfferDetail = {
  id: "20000000-0000-4000-8000-000000000001",
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

class OfferNotFoundError extends Error {
  override name = "OfferNotFoundError";
}

function DrawerHarness({
  offerId,
  matchesFilters = true,
  onClose = () => undefined,
}: {
  offerId: string;
  matchesFilters?: boolean;
  onClose?: () => void;
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
      onClose={onClose}
      returnFocusRef={returnFocusRef}
    />
  );
}

function renderDrawer(offerId = detail.id) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DrawerHarness offerId={offerId} />
    </QueryClientProvider>,
  );
}

describe("OfferDetailDrawer", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders masked detail fields and verified Telegram link", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer();

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getByText("Masked public text only.")).toBeInTheDocument();
    expect(
      screen.getByText("detailAvailabilityDisclaimer"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("href", "https://t.me/elestate_warszawa/42");
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows non-link fallback when verified url is absent", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: { ...detail, verified_source_url: null },
    });
    renderDrawer();

    expect(
      await screen.findByText(/detailSourceFallbackWithId/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "detailOpenTelegram" }),
    ).not.toBeInTheDocument();
  });

  it("announces not-found without leaking payloads", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "not_found",
    });
    renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "detailNotFound",
    );
  });

  it("closes from escape and restores focus to the trigger", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();

    function ClosableDrawer() {
      const [open, setOpen] = useState(true);
      return (
        <OfferDetailDrawer
          open={open}
          offerId={detail.id}
          matchesFilters={false}
          detailQuery={
            {
              data: detail,
              error: null,
              isError: false,
              isPending: false,
              isSuccess: true,
            } as never
          }
          onClose={() => setOpen(false)}
          returnFocusRef={{ current: trigger }}
        />
      );
    }

    render(<ClosableDrawer />);
    await userEvent.keyboard("{Escape}");
    await waitFor(() =>
      expect(
        screen.queryByTestId("offer-detail-overlay"),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });
});
