"use client";

import type { FeatureCollection, Point } from "geojson";
import type { GeoJSONSource } from "maplibre-gl";
import {
  AttributionControl,
  Layer,
  Map,
  NavigationControl,
  Source,
  type LayerProps,
  type MapLayerMouseEvent,
} from "react-map-gl/maplibre";

import type { LocationMap } from "@/lib/catalog-api";

const MAP_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL?.trim() ||
  "https://tiles.openfreemap.org/styles/liberty";

const clusterLayer: LayerProps = {
  id: "location-clusters",
  type: "circle" as const,
  source: "locations",
  filter: ["has", "point_count"],
  paint: {
    "circle-color": "#154f3b",
    "circle-radius": ["step", ["get", "point_count"], 20, 10, 26, 50, 34],
    "circle-stroke-color": "#ffffff",
    "circle-stroke-width": 2,
  },
};

const clusterCountLayer: LayerProps = {
  id: "location-cluster-count",
  type: "symbol" as const,
  source: "locations",
  filter: ["has", "point_count"],
  layout: {
    "text-field": ["get", "point_count_abbreviated"],
    "text-size": 13,
  },
  paint: { "text-color": "#ffffff" },
};

const locationLayer: LayerProps = {
  id: "locations-unclustered",
  type: "circle" as const,
  source: "locations",
  filter: ["!", ["has", "point_count"]],
  paint: {
    "circle-color": [
      "case",
      ["==", ["get", "confidence"], "low"],
      "#c65f24",
      "#2b7d58",
    ],
    "circle-radius": [
      "interpolate",
      ["linear"],
      ["get", "matching_offer_count"],
      1,
      9,
      5,
      15,
    ],
    "circle-stroke-color": "#ffffff",
    "circle-stroke-width": 2,
  },
};

type WarsawMapProps = {
  data: LocationMap;
  selectedId: string | null;
  onSelect: (locationId: string) => void;
  onFailure: () => void;
};

export function WarsawMap({
  data,
  selectedId,
  onSelect,
  onFailure,
}: WarsawMapProps) {
  const geojson = data as FeatureCollection<Point>;

  async function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0];
    if (!feature) return;

    const clusterId = feature.properties?.cluster_id;
    if (typeof clusterId === "number") {
      const source = event.target.getSource("locations") as
        GeoJSONSource | undefined;
      const coordinates =
        feature.geometry.type === "Point"
          ? (feature.geometry.coordinates as [number, number])
          : null;
      if (!source || !coordinates) return;
      const zoom = await source.getClusterExpansionZoom(clusterId);
      event.target.easeTo({ center: coordinates, zoom });
      return;
    }

    if (typeof feature.id === "string") {
      onSelect(feature.id);
    }
  }

  return (
    <div className="map-canvas" aria-label="Interactive map of Warsaw">
      <Map
        initialViewState={{
          longitude: 21.0122,
          latitude: 52.2297,
          zoom: 10.4,
        }}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={["location-clusters", "locations-unclustered"]}
        onClick={(event) => void handleClick(event)}
        onError={onFailure}
        cursor="pointer"
        attributionControl={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <AttributionControl
          position="bottom-right"
          customAttribution="© OpenFreeMap · © OpenStreetMap contributors"
        />
        <Source
          id="locations"
          type="geojson"
          data={geojson}
          cluster
          clusterMaxZoom={14}
          clusterRadius={44}
          generateId={false}
        >
          <Layer {...clusterLayer} />
          <Layer {...clusterCountLayer} />
          <Layer {...locationLayer} />
          {selectedId ? (
            <Layer
              id="location-selected"
              type="circle"
              source="locations"
              filter={["==", ["id"], selectedId]}
              paint={{
                "circle-color": "transparent",
                "circle-radius": 18,
                "circle-stroke-color": "#17201b",
                "circle-stroke-width": 3,
              }}
            />
          ) : null}
        </Source>
      </Map>
    </div>
  );
}
