import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MapFilterControls } from "@/components/map-filter-controls";
import type { FilterFacets } from "@/lib/catalog-api";
import { DEFAULT_MAP_SEARCH_STATE } from "@/lib/map-search-params";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { room?: number }) =>
    values?.room === undefined ? key : `${key}:${values.room}`,
}));

const facets: FilterFacets = {
  districts: ["ochota", "wola"],
  rooms: [1, 2, 3],
  market_types: ["primary", "secondary"],
  content_types: ["development", "unit"],
  price_min_minor: 50_000_000,
  price_max_minor: 150_000_000,
  area_min_sqm: "25.0",
  area_max_sqm: "100.0",
  published_from: "2026-01-01T00:00:00Z",
  published_to: "2026-12-31T00:00:00Z",
};

describe("MapFilterControls", () => {
  afterEach(cleanup);

  it("applies every M1 filter as one state change", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    render(
      <MapFilterControls
        facets={facets}
        facetsError={false}
        facetsLoading={false}
        state={DEFAULT_MAP_SEARCH_STATE}
        onApply={onApply}
        onClear={vi.fn()}
      />,
    );

    await user.type(
      screen.getByRole("spinbutton", { name: "minimumPrice" }),
      "800000",
    );
    await user.type(
      screen.getByRole("spinbutton", { name: "maximumPrice" }),
      "1250000",
    );
    await user.type(
      screen.getByRole("spinbutton", { name: "minimumArea" }),
      "35",
    );
    await user.type(
      screen.getByRole("spinbutton", { name: "maximumArea" }),
      "71.5",
    );
    await user.click(screen.getByRole("checkbox", { name: "roomOption:2" }));
    await user.click(screen.getByRole("checkbox", { name: "Wola" }));
    await user.click(
      screen.getByRole("checkbox", { name: "marketType.secondary" }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: "contentType.development" }),
    );
    fireEvent.change(screen.getByLabelText("publishedFrom"), {
      target: { value: "2026-08-01" },
    });
    fireEvent.change(screen.getByLabelText("publishedTo"), {
      target: { value: "2026-08-31" },
    });
    await user.click(screen.getByRole("button", { name: "applyFilters" }));

    expect(onApply).toHaveBeenCalledWith({
      ...DEFAULT_MAP_SEARCH_STATE,
      priceMinMinor: 80_000_000,
      priceMaxMinor: 125_000_000,
      areaMin: "35",
      areaMax: "71.5",
      rooms: [2],
      districts: ["wola"],
      marketTypes: ["secondary"],
      contentTypes: ["unit"],
      publishedFrom: "2026-08-01T00:00:00.000Z",
      publishedTo: "2026-08-31T23:59:59.999Z",
    });
  });

  it("keeps controls usable when facets fail and clears deterministically", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();
    render(
      <MapFilterControls
        facets={null}
        facetsError
        facetsLoading={false}
        state={{
          ...DEFAULT_MAP_SEARCH_STATE,
          districts: ["srodmiescie"],
          rooms: [2],
        }}
        onApply={vi.fn()}
        onClear={onClear}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("facetsError");
    expect(screen.getByRole("checkbox", { name: "Srodmiescie" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "clearFilters" }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("renders only facet-provided options while facets are unavailable", () => {
    render(
      <MapFilterControls
        facets={null}
        facetsError={false}
        facetsLoading
        state={DEFAULT_MAP_SEARCH_STATE}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("facetsLoading");
    // Rooms, districts, and market options come only from facets, so none
    // render while the facet snapshot is unavailable.
    expect(
      screen.queryByRole("checkbox", { name: "roomOption:1" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: "marketType.primary" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: "marketType.unknown" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: "Wola" }),
    ).not.toBeInTheDocument();
    // Active URL state stays visible: both default content types remain
    // checked and selectable even without a facet snapshot.
    expect(
      screen.getByRole("checkbox", { name: "contentType.development" }),
    ).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "contentType.unit" }),
    ).toBeChecked();
  });

  it("clears blank numeric and date fields instead of inventing values", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    render(
      <MapFilterControls
        facets={facets}
        facetsError={false}
        facetsLoading={false}
        state={{
          ...DEFAULT_MAP_SEARCH_STATE,
          priceMinMinor: 80_000_000,
          publishedFrom: "2026-08-01T00:00:00.000Z",
          publishedTo: "2026-08-31T23:59:59.999Z",
        }}
        onApply={onApply}
        onClear={vi.fn()}
      />,
    );

    await user.clear(screen.getByRole("spinbutton", { name: "minimumPrice" }));
    await user.type(
      screen.getByRole("spinbutton", { name: "maximumPrice" }),
      "not-a-number",
    );
    fireEvent.change(screen.getByLabelText("publishedFrom"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("publishedTo"), {
      target: { value: "" },
    });
    await user.click(screen.getByRole("button", { name: "applyFilters" }));

    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({
        priceMinMinor: null,
        priceMaxMinor: null,
        publishedFrom: null,
        publishedTo: null,
      }),
    );
  });
});
