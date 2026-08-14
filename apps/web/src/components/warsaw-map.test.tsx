import { act, cleanup, render, screen } from "@testing-library/react";
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
    }: {
      children: ReactNode;
      onClick: (event: object) => void;
      onLoad: () => void;
      onMoveEnd: (event: object) => void;
    },
    ref,
  ) {
    useImperativeHandle(ref, () => ({
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
    >
      {children}
    </div>
  ),
  Layer: ({ id, layout }: { id: string; layout?: Record<string, unknown> }) => (
    <div
      data-testid={`layer-${id}`}
      data-text-font={JSON.stringify(layout?.["text-font"])}
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
    expect(setWorkerUrl).toHaveBeenCalledWith(
      "/vendor/maplibre/maplibre-gl-worker.mjs",
    );
    clickedFeature = {
      id: "10000000-0000-4000-8000-000000000001",
      properties: {},
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
});
