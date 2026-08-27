import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { forwardRef, useImperativeHandle, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarsawMap } from "@/components/warsaw-map";
import type { LocationMap } from "@/lib/catalog-api";

const setWorkerUrl = vi.hoisted(() => vi.fn());

vi.mock("maplibre-gl", () => ({ setWorkerUrl }));

const easeTo = vi.fn();
const fitBounds = vi.fn();
const getClusterExpansionZoom = vi.fn(async () => 13);
let clickedFeature: object = {
  id: "10000000-0000-4000-8000-000000000001",
  properties: {},
  geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
};

vi.mock("react-map-gl/maplibre", () => ({
  Map: forwardRef(function FakeMap(
    {
      children,
      onClick,
      onLoad,
      onMoveEnd,
      onError,
    }: {
      children: ReactNode;
      onClick: (event: object) => void;
      onLoad: () => void;
      onMoveEnd: (event: object) => void;
      onError: () => void;
    },
    ref,
  ) {
    useImperativeHandle(ref, () => ({
      getBounds: () => ({
        getWest: () => 20.8,
        getSouth: () => 52.1,
        getEast: () => 21.2,
        getNorth: () => 52.4,
      }),
      easeTo: (options: object) => {
        easeTo(options);
      },
      fitBounds: (
        bounds: [[number, number], [number, number]],
        options: object,
      ) => {
        fitBounds(bounds, options);
        onMoveEnd({
          target: {
            getBounds: () => ({
              getWest: () => bounds[0][0],
              getSouth: () => bounds[0][1],
              getEast: () => bounds[1][0],
              getNorth: () => bounds[1][1],
            }),
          },
        });
      },
    }));
    return (
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
        <button
          type="button"
          onClick={() =>
            onMoveEnd({
              target: {
                getBounds: () => ({
                  getWest: () => 20.81234549,
                  getSouth: () => 52.12345651,
                  getEast: () => 21.2,
                  getNorth: () => 52.3,
                }),
              },
            })
          }
        >
          simulated-map-move
        </button>
        <button
          type="button"
          onClick={() =>
            onMoveEnd({
              target: {
                getBounds: () => ({
                  getWest: () => 20.8,
                  getSouth: () => 52.3,
                  getEast: () => 21.2,
                  getNorth: () => 52.3,
                }),
              },
            })
          }
        >
          simulated-map-move-flat
        </button>
        <button type="button" onClick={onError}>
          simulated-map-error
        </button>
        {children}
      </div>
    );
  }),
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
      data-source-json={
        typeof data === "string" ? undefined : JSON.stringify(data)
      }
    >
      {children}
    </div>
  ),
  Layer: ({
    id,
    layout,
    filter,
  }: {
    id: string;
    layout?: Record<string, unknown>;
    filter?: unknown;
  }) => (
    <div
      data-testid={`layer-${id}`}
      data-text-font={JSON.stringify(layout?.["text-font"])}
      data-filter={JSON.stringify(filter)}
    />
  ),
  NavigationControl: () => null,
  AttributionControl: ({
    customAttribution,
  }: {
    customAttribution: string;
  }) => <span>{customAttribution}</span>,
}));

const mapData: LocationMap = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "10000000-0000-4000-8000-000000000001",
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
      properties: {
        display_name: "Synthetic Central Residence",
        display_address: "Synthetic address, Warsaw",
        district: "srodmiescie",
        coordinate_precision: "district",
        confidence: "low",
        matching_offer_count: 1,
        total_offer_count: 1,
        latest_published_at: "2026-08-01T10:00:00Z",
        price_min_minor: 80_000_000,
        price_max_minor: 80_000_000,
        area_min_sqm: "35.00",
        area_max_sqm: "35.00",
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

describe("WarsawMap", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("selects an unclustered backend feature and shows attribution", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    expect(setWorkerUrl).toHaveBeenCalledWith(
      "/vendor/maplibre/maplibre-gl-worker.mjs",
    );
    clickedFeature = {
      // This mirrors MapLibre's vector-tile conversion of the UUID feature id.
      id: 10_000_000,
      properties: {
        location_id: "10000000-0000-4000-8000-000000000001",
      },
      geometry: { type: "Point", coordinates: [21.0122, 52.2297] },
    };
    render(
      <WarsawMap
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={onSelect}
        onFailure={vi.fn()}
        onViewportChange={vi.fn()}
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
    expect(screen.getByTestId("source-locations")).toHaveAttribute(
      "data-source-json",
      expect.stringContaining(
        '"location_id":"10000000-0000-4000-8000-000000000001"',
      ),
    );
    expect(screen.getByTestId("layer-warsaw-district-labels")).toHaveAttribute(
      "data-text-font",
      '["Noto Sans Regular"]',
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
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={onSelect}
        onFailure={vi.fn()}
        onViewportChange={vi.fn()}
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
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={vi.fn()}
        onFailure={onFailure}
        onViewportChange={vi.fn()}
      />,
    );

    act(() => vi.advanceTimersByTime(14_999));
    expect(onFailure).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onFailure).toHaveBeenCalledOnce();
  });

  it("reports a normalized viewport after movement", async () => {
    const user = userEvent.setup();
    const onViewportChange = vi.fn();
    render(
      <WarsawMap
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={vi.fn()}
        onFailure={vi.fn()}
        onViewportChange={onViewportChange}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-move" }),
    );

    expect(onViewportChange).toHaveBeenCalledWith(
      "20.812345,52.123457,21.2,52.3",
    );
  });

  it("ignores a degenerate viewport reported mid-resize", async () => {
    const user = userEvent.setup();
    const onViewportChange = vi.fn();
    render(
      <WarsawMap
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={vi.fn()}
        onFailure={vi.fn()}
        onViewportChange={onViewportChange}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-move-flat" }),
    );

    expect(onViewportChange).not.toHaveBeenCalled();
  });

  it("fits the rendered map to a bounded URL viewport", async () => {
    const user = userEvent.setup();
    const props = {
      data: mapData,
      selectedId: null,
      loadingLabel: "Loading interactive map",
      onSelect: vi.fn(),
      onFailure: vi.fn(),
      onViewportChange: vi.fn(),
    };
    const view = render(<WarsawMap bbox="20.7,52.0,21.4,52.4" {...props} />);

    await user.click(
      screen.getByRole("button", { name: "simulated-map-load" }),
    );
    view.rerender(<WarsawMap bbox="20.65,51.8,21.45,52.6" {...props} />);

    expect(fitBounds).toHaveBeenLastCalledWith(
      [
        [20.65, 51.8],
        [21.45, 52.6],
      ],
      { duration: 0, padding: 32 },
    );
    expect(props.onViewportChange).not.toHaveBeenCalled();
  });

  it("does not refit when the URL catches up with the reported viewport", async () => {
    const user = userEvent.setup();
    const props = {
      data: mapData,
      selectedId: null,
      loadingLabel: "Loading interactive map",
      onSelect: vi.fn(),
      onFailure: vi.fn(),
      onViewportChange: vi.fn(),
    };
    const view = render(<WarsawMap bbox="20.7,52.0,21.4,52.4" {...props} />);

    await user.click(
      screen.getByRole("button", { name: "simulated-map-load" }),
    );
    await user.click(
      screen.getByRole("button", { name: "simulated-map-move" }),
    );
    expect(props.onViewportChange).toHaveBeenCalledWith(
      "20.812345,52.123457,21.2,52.3",
    );
    fitBounds.mockClear();

    view.rerender(
      <WarsawMap bbox="20.812345,52.123457,21.2,52.3" {...props} />,
    );

    expect(fitBounds).not.toHaveBeenCalled();
  });

  it("ignores clicks without a selectable feature and reports map errors", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onFailure = vi.fn();
    clickedFeature = { properties: {}, geometry: { type: "LineString" } };
    const { rerender } = render(
      <WarsawMap
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId="10000000-0000-4000-8000-000000000001"
        highlightedId="10000000-0000-4000-8000-000000000002"
        loadingLabel="Loading interactive map"
        onSelect={onSelect}
        onFailure={onFailure}
        onViewportChange={vi.fn()}
      />,
    );

    expect(screen.getByTestId("layer-location-selected")).toHaveAttribute(
      "data-filter",
      '["==",["get","location_id"],"10000000-0000-4000-8000-000000000001"]',
    );
    expect(screen.getByTestId("layer-location-highlighted")).toHaveAttribute(
      "data-filter",
      '["==",["get","location_id"],"10000000-0000-4000-8000-000000000002"]',
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );
    expect(onSelect).not.toHaveBeenCalled();

    clickedFeature = {
      id: 7,
      properties: { cluster_id: 42 },
      geometry: { type: "Polygon" },
    };
    rerender(
      <WarsawMap
        bbox="not-a-bbox"
        data={mapData}
        selectedId={null}
        highlightedId={null}
        loadingLabel="Loading interactive map"
        onSelect={onSelect}
        onFailure={onFailure}
        onViewportChange={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );
    expect(easeTo).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "simulated-map-error" }),
    );
    expect(onFailure).toHaveBeenCalled();
  });

  it("skips cluster animation when the user prefers reduced motion", async () => {
    const user = userEvent.setup();
    clickedFeature = {
      id: 7,
      properties: { cluster_id: 42 },
      geometry: { type: "Point", coordinates: [21.0, 52.2] },
    };
    render(
      <WarsawMap
        bbox="20.7,52.0,21.4,52.4"
        data={mapData}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={vi.fn()}
        onFailure={vi.fn()}
        onViewportChange={vi.fn()}
        reduceMotion
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "simulated-map-click" }),
    );
    expect(easeTo).toHaveBeenCalledWith({
      center: [21.0, 52.2],
      zoom: 13,
      duration: 0,
    });
  });
  it("recenters only when the focus target leaves the comfortable core", async () => {
    const user = userEvent.setup();
    const data = mapData;
    const { rerender } = render(
      <WarsawMap
        bbox="20.8,52.1,21.2,52.4"
        data={data}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={() => undefined}
        onFailure={() => undefined}
        onViewportChange={() => undefined}
        focusTarget={{ longitude: 21.0, latitude: 52.25, nonce: 1 }}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "simulated-map-load" }),
    );
    expect(easeTo).not.toHaveBeenCalled();

    rerender(
      <WarsawMap
        bbox="20.8,52.1,21.2,52.4"
        data={data}
        selectedId={null}
        loadingLabel="Loading interactive map"
        onSelect={() => undefined}
        onFailure={() => undefined}
        onViewportChange={() => undefined}
        focusTarget={{ longitude: 20.81, latitude: 52.39, nonce: 2 }}
      />,
    );
    await waitFor(() => expect(easeTo).toHaveBeenCalledTimes(1));
    expect(easeTo).toHaveBeenCalledWith(
      expect.objectContaining({ center: [20.81, 52.39] }),
    );
  });
});
