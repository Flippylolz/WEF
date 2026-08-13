"use client";

import type { FeatureCollection, Point } from "geojson";
import { setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
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
const MAPLIBRE_WORKER = "/vendor/maplibre/maplibre-gl-worker.mjs";
const DISTRICT_BOUNDARIES = "/data/warsaw-districts.geojson";
const MAP_LOAD_TIMEOUT_MS = 15_000;

setWorkerUrl(MAPLIBRE_WORKER);

const districtFillLayer: LayerProps = {
  id: "warsaw-district-fills",
  type: "fill" as const,
  source: "warsaw-districts",
  paint: {
    "fill-color": "#2b7d58",
    "fill-opacity": 0.08,
  },
};

const districtLineLayer: LayerProps = {
  id: "warsaw-district-lines",
  type: "line" as const,
  source: "warsaw-districts",
  paint: {
    "line-color": "#154f3b",
    "line-opacity": 0.9,
    "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.5, 13, 3],
  },
};

const districtLabelLayer: LayerProps = {
  id: "warsaw-district-labels",
  type: "symbol" as const,
  source: "warsaw-districts",
  minzoom: 9,
  layout: {
    "text-field": ["get", "name"],
    "text-font": ["Noto Sans Regular"],
    "text-size": ["interpolate", ["linear"], ["zoom"], 9, 10, 12, 13],
    "text-letter-spacing": 0.05,
  },
  paint: {
    "text-color": "#154f3b",
    "text-halo-color": "rgba(255, 255, 255, 0.92)",
    "text-halo-width": 1.5,
  },
};

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
  loadingLabel: string;
  onSelect: (locationId: string) => void;
  onFailure: () => void;
};

export function WarsawMap({
  data,
  selectedId,
  loadingLabel,
  onSelect,
  onFailure,
}: WarsawMapProps) {
  const geojson = data as FeatureCollection<Point>;
  const [mapReady, setMapReady] = useState(false);
  const mapLoaded = useRef(false);
  const failureHandler = useRef(onFailure);

  useEffect(() => {
    failureHandler.current = onFailure;
  }, [onFailure]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      if (!mapLoaded.current) failureHandler.current();
    }, MAP_LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, []);

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
      {!mapReady ? (
        <div className="map-loading" role="status">
          {loadingLabel}
        </div>
      ) : null}
      <Map
        initialViewState={{
          longitude: 21.0122,
          latitude: 52.2297,
          zoom: 10.4,
        }}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={["location-clusters", "locations-unclustered"]}
        onClick={(event) => void handleClick(event)}
        onLoad={() => {
          mapLoaded.current = true;
          setMapReady(true);
        }}
        cursor="pointer"
        attributionControl={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <AttributionControl
          position="bottom-right"
          customAttribution="© OpenFreeMap · © OpenStreetMap contributors"
        />
        <Source id="warsaw-districts" type="geojson" data={DISTRICT_BOUNDARIES}>
          <Layer {...districtFillLayer} />
          <Layer {...districtLineLayer} />
          <Layer {...districtLabelLayer} />
        </Source>
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
