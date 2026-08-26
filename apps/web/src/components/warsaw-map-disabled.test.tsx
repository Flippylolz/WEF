import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LocationMap } from "@/lib/catalog-api";

vi.mock("maplibre-gl", () => ({ setWorkerUrl: vi.fn() }));
vi.mock("react-map-gl/maplibre", () => ({
  Map: () => {
    throw new Error("map should not mount when disabled");
  },
  Source: () => null,
  Layer: () => null,
  NavigationControl: () => null,
  AttributionControl: () => null,
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

describe("WarsawMap with the map disabled", () => {
  afterEach(() => {
    cleanup();
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it("reports failure immediately and renders nothing", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEF_DISABLE_MAP", "1");
    vi.resetModules();
    const { WarsawMap } = await import("@/components/warsaw-map");
    const onFailure = vi.fn();
    const { container } = render(
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

    expect(onFailure).toHaveBeenCalledOnce();
    expect(container).toBeEmptyDOMElement();
  });
});
