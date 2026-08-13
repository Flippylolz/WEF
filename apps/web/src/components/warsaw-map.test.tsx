import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarsawMap } from "@/components/warsaw-map";
import type { LocationMap } from "@/lib/catalog-api";

const easeTo = vi.fn();
const getClusterExpansionZoom = vi.fn(async () => 13);
let clickedFeature: object = {
  id: "10000000-0000-4000-8000-000000000001",
  properties: {},
  geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
};

vi.mock("react-map-gl/maplibre", () => ({
  Map: ({
    children,
    onClick,
  }: {
    children: ReactNode;
    onClick: (event: object) => void;
  }) => (
    <div>
      <button
        type="button"
        onClick={() =>
          onClick({
            features: [clickedFeature],
            target: {
              getSource: () => ({ getClusterExpansionZoom }),
              easeTo,
            },
          })
        }
      >
        simulated-map-click
      </button>
      {children}
    </div>
  ),
  Source: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Layer: () => null,
  NavigationControl: () => null,
  AttributionControl: ({
    customAttribution,
  }: {
    customAttribution: string;
  }) => <span>{customAttribution}</span>,
}));

const mapData: LocationMap = {
  type: "FeatureCollection",
  features: [],
  meta: {
    request_id: "00000000-0000-4000-8000-000000000001",
    feature_count: 0,
    matching_offer_count: 0,
  },
};

describe("WarsawMap", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("selects an unclustered backend feature and shows attribution", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    clickedFeature = {
      id: "10000000-0000-4000-8000-000000000001",
      properties: {},
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
    };
    render(
      <WarsawMap
        data={mapData}
        selectedId={null}
        onSelect={onSelect}
        onFailure={vi.fn()}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );

    expect(onSelect).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    expect(
      screen.getByText("© OpenFreeMap · © OpenStreetMap contributors"),
    ).toBeInTheDocument();
  });

  it("expands a cluster instead of selecting a location", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    clickedFeature = {
      id: 7,
      properties: { cluster_id: 42 },
      geometry: { type: "Point", coordinates: [21.0, 52.2] },
    };
    render(
      <WarsawMap
        data={mapData}
        selectedId={null}
        onSelect={onSelect}
        onFailure={vi.fn()}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );

    expect(getClusterExpansionZoom).toHaveBeenCalledWith(42);
    expect(easeTo).toHaveBeenCalledWith({
      center: [21.0, 52.2],
      zoom: 13,
    });
    expect(onSelect).not.toHaveBeenCalled();
  });
});
