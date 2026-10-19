import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { LocationMapFeature, LocationOfferPage } from "@/lib/catalog-api";
import { OfferPanel } from "./offer-panel";

vi.mock("next-intl", () => ({ useTranslations: () => (key: string) => key }));
afterEach(cleanup);

const feature: LocationMapFeature = {
  type: "Feature",
  id: "location",
  geometry: { type: "Point", coordinates: [21, 52.2] },
  properties: {
    display_name: "Selected residence",
    display_address: "Example street",
    district: null,
    coordinate_precision: "district",
    confidence: "low",
    matching_offer_count: 1,
    total_offer_count: 1,
    latest_published_at: "2026-08-01T10:00:00Z",
    currency: "PLN",
  },
};
const sparseOffer: LocationOfferPage["items"][number] = {
  id: "offer",
  content_type: "unit",
  market_type: "secondary",
  property_type: "apartment",
  display_name: "Sparse offer",
  data_confidence: "partial",
  data_origin: "parser",
  published_at: "2026-08-01T10:00:00Z",
  currency: "PLN",
  matches_filters: false,
  delivery_label: null,
  floor_label: null,
  parking_included_in_price: false,
  storage_included_in_price: false,
};
const page: LocationOfferPage = {
  location: { id: "location", ...feature.properties },
  items: [sparseOffer],
  matching_count: 0,
  total_count: 1,
  next_cursor: null,
};
const callbacks = () => ({ onOfferTrigger: vi.fn(), onSelectOffer: vi.fn() });

it("prompts for a location before a selection or catalog response exists", () => {
  render(
    <OfferPanel feature={null} offers={{ status: "idle" }} {...callbacks()} />,
  );
  expect(screen.getByText("selectLocation")).toBeVisible();
});

it("shows loading even before the selected location has arrived", () => {
  render(
    <OfferPanel
      feature={null}
      offers={{ status: "loading" }}
      {...callbacks()}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("offersLoading");
});

it("renders failed selected-location requests with an optional retry", async () => {
  const onRetry = vi.fn();
  const props = {
    feature,
    offers: { status: "error" } as const,
    ...callbacks(),
  };
  const { rerender } = render(<OfferPanel {...props} />);
  expect(screen.getByRole("alert")).toHaveTextContent("offersError");
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  rerender(<OfferPanel {...props} onRetry={onRetry} />);
  await userEvent.click(screen.getByRole("button", { name: "retry" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("shows empty results while a selected location waits or has no offers", () => {
  const props = { feature, ...callbacks() };
  const { rerender } = render(
    <OfferPanel {...props} offers={{ status: "idle" }} />,
  );
  expect(screen.getByText("offersEmpty")).toBeVisible();
  rerender(
    <OfferPanel
      {...props}
      offers={{ status: "ready", data: { ...page, items: [] } }}
    />,
  );
  expect(screen.getByText("offersEmpty")).toBeVisible();
});

it("uses response location details when the map no longer includes the selection", async () => {
  const handlers = callbacks();
  render(
    <OfferPanel
      feature={null}
      offers={{ status: "ready", data: page }}
      {...handlers}
    />,
  );
  expect(
    screen.getByRole("heading", { name: "Selected residence" }),
  ).toBeVisible();
  expect(screen.getByText("nonMatchingOffer")).toBeVisible();
  expect(screen.getByText("partialData")).toBeVisible();
  expect(screen.queryByText("apartmentPrice")).not.toBeInTheDocument();
  expect(screen.queryByText(/m²/)).not.toBeInTheDocument();
  const trigger = screen.getByRole("button", { name: "viewOfferDetails" });
  await userEvent.click(trigger);
  expect(handlers.onSelectOffer).toHaveBeenCalledWith("offer", false, trigger);
  expect(handlers.onOfferTrigger).toHaveBeenCalledWith("offer", trigger);
});

it("treats omitted additional prices and area endpoints as unknown", () => {
  const data = JSON.parse(
    JSON.stringify({
      ...page,
      items: [
        {
          ...sparseOffer,
          parking_included_in_price: undefined,
          storage_included_in_price: undefined,
          area_min_sqm: "35",
          area_max_sqm: "35",
        },
      ],
    }),
  ) as LocationOfferPage;
  render(
    <OfferPanel
      feature={null}
      offers={{ status: "ready", data }}
      {...callbacks()}
    />,
  );
  expect(screen.getByText(/35.*m²/)).toBeVisible();
  expect(screen.queryByText("parkingPrice")).not.toBeInTheDocument();
  expect(screen.queryByText("storagePrice")).not.toBeInTheDocument();
});
