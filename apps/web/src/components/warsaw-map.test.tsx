import { act, cleanup, render, screen } from "@testing-library/react";
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
    onLoad,
  }: {
    children: ReactNode;
    onClick: (event: object) => void;
    onLoad: () => void;
  }) => (
    <div>
      <button type="button" onClick={onLoad}>
        simulated-map-load
      </button>
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
  Source: ({
    children,
    data,
    id,
  }: {
    children: ReactNode;
    data: object | string;
    id: string;
  }) => (
    <div
      data-testid={`source-${id}`}
      data-source-url={typeof data === "string" ? data : undefined}
    >
      {children}
    </div>
  ),
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
    vi.useRealTimers();
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
        loadingLabel="Loading interactive map"
        onSelect={onSelect}
        onFailure={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading interactive map",
    );
    await user.click(
      screen.getByRole("button", { name: "simulated-map-load" }),
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );

    expect(onSelect).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    expect(
      screen.getByText("© OpenFreeMap · © OpenStreetMap contributors"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("source-warsaw-districts")).toHaveAttribute(
      "data-source-url",
      "/data/warsaw-districts.geojson",
    );
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
        loadingLabel="Loading interactive map"
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

  it("reports failure only after the map load timeout", () => {
    vi.useFakeTimers();
    const onFailure = vi.fn();

    render(
      <WarsawMap
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={vi.fn()}
        onFailure={onFailure}
      />,
    );

    act(() => vi.advanceTimersByTime(14_999));
    expect(onFailure).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onFailure).toHaveBeenCalledOnce();
  });
});
