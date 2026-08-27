"use client";

import type { FeatureCollection, Point } from "geojson";
import { setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AttributionControl,
  Layer,
  Map,
  NavigationControl,
  Source,
  type LayerProps,
  type MapLayerMouseEvent,
  type MapRef,
  type ViewStateChangeEvent,
} from "react-map-gl/maplibre";

import { isWithinComfortRegion, type FocusTarget } from "@/lib/listing-focus";
import { boundedWarsawViewport, parseBbox } from "@/lib/map-search-params";

import type { LocationMap } from "@/lib/catalog-api";
import { recordMapConstruction } from "@/lib/map-lifecycle";

const MAP_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL?.trim() ||
  "https://tiles.openfreemap.org/styles/dark";
const MAP_DISABLED = process.env.NEXT_PUBLIC_WEF_DISABLE_MAP === "1";
const MAPLIBRE_WORKER = "/vendor/maplibre/maplibre-gl-worker.mjs";
const DISTRICT_BOUNDARIES = "/data/warsaw-districts.geojson";
const MAP_LOAD_TIMEOUT_MS = 15_000;

setWorkerUrl(MAPLIBRE_WORKER);

const districtFillLayer: LayerProps = {
  id: "warsaw-district-fills",
  type: "fill" as const,
  source: "warsaw-districts",
  paint: {
    "fill-color": "#3fb950",
    "fill-opacity": 0.05,
  },
};

const districtLineLayer: LayerProps = {
  id: "warsaw-district-lines",
  type: "line" as const,
  source: "warsaw-districts",
  paint: {
    "line-color": "#30363d",
    "line-opacity": 0.85,
    "line-width": ["interpolate", ["linear"], ["zoom"], 9, 1.5, 13, 2.5],
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
    "text-color": "#8b949e",
    "text-halo-color": "rgba(13, 17, 23, 0.92)",
    "text-halo-width": 1.5,
  },
};

const clusterLayer: LayerProps = {
  id: "location-clusters",
  type: "circle" as const,
  source: "locations",
  filter: ["has", "point_count"],
  paint: {
    "circle-color": "#262c36",
    "circle-radius": ["step", ["get", "point_count"], 20, 10, 26, 50, 34],
    "circle-stroke-color": "#3fb950",
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
  paint: { "text-color": "#e6edf3" },
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
      "#d29922",
      "#3fb950",
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
    "circle-stroke-color": "#0d1117",
    "circle-stroke-width": 2,
  },
};

type WarsawMapProps = {
  bbox: string;
  data: LocationMap;
  selectedId: string | null;
  highlightedId?: string | null;
  focusTarget?: FocusTarget | null;
  loadingLabel: string;
  onSelect: (locationId: string) => void;
  onFailure: () => void;
  onViewportChange: (bbox: string) => void;
  reduceMotion?: boolean;
};

export function WarsawMap({
  bbox,
  data,
  selectedId,
  highlightedId = null,
  focusTarget = null,
  loadingLabel,
  onSelect,
  onFailure,
  onViewportChange,
  reduceMotion = false,
}: WarsawMapProps) {
  const geojson = useMemo<FeatureCollection<Point>>(
    () => ({
      ...data,
      features: data.features.map((feature) => ({
        ...feature,
        // MapLibre's vector-tile wrapper coerces a GeoJSON feature id through
        // parseInt, so UUID ids can be truncated or dropped. Properties retain
        // the full string through clustering and rendered-feature queries.
        properties: { ...feature.properties, location_id: feature.id },
      })),
    }),
    [data],
  );
  const [mapReady, setMapReady] = useState(false);
  const mapRef = useRef<MapRef>(null);
  const mapLoaded = useRef(false);
  const failureHandler = useRef(onFailure);
  const suppressNextMoveEnd = useRef(false);
  const lastReportedViewport = useRef<string | null>(null);
  const initialBounds = parseBbox(bbox);

  useEffect(() => {
    recordMapConstruction();
  }, []);

  useEffect(() => {
    failureHandler.current = onFailure;
  }, [onFailure]);

  useEffect(() => {
    if (!MAP_DISABLED) return;
    failureHandler.current();
  }, []);

  useEffect(() => {
    if (MAP_DISABLED) return;
    const timeout = window.setTimeout(() => {
      if (!mapLoaded.current) failureHandler.current();
    }, MAP_LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (MAP_DISABLED) return;
    if (!mapReady) return;
    const bounds = parseBbox(bbox);
    if (bounds === null) return;
    if (bbox === lastReportedViewport.current) return;
    suppressNextMoveEnd.current = true;
    mapRef.current?.fitBounds(
      [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]],
      ],
      { duration: 0, padding: 32 },
    );
  }, [bbox, mapReady]);

  useEffect(() => {
    if (MAP_DISABLED || !mapReady || focusTarget === null) return;
    const map = mapRef.current;
    if (map === null) return;
    const point: [number, number] = [
      focusTarget.longitude,
      focusTarget.latitude,
    ];
    if (isWithinComfortRegion(map.getBounds(), point)) return;
    map.easeTo({
      center: point,
      duration: reduceMotion ? 0 : 600,
    });
    // The ease triggers moveend on purpose: the URL bbox then reflects the
    // newly centered viewport, so results stay bound to the visible area.
  }, [focusTarget, mapReady, reduceMotion]);

  if (MAP_DISABLED) {
    return null;
  }

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
      event.target.easeTo({
        center: coordinates,
        zoom,
        duration: reduceMotion ? 0 : undefined,
      });
      return;
    }

    const locationId = feature.properties?.location_id;
    if (typeof locationId === "string") {
      onSelect(locationId);
    }
  }

  function handleMoveEnd(event: ViewStateChangeEvent) {
    if (suppressNextMoveEnd.current) {
      suppressNextMoveEnd.current = false;
      return;
    }
    const bounds = event.target.getBounds();
    const west = bounds.getWest();
    const south = bounds.getSouth();
    const east = bounds.getEast();
    const north = bounds.getNorth();
    // A flat viewport (unsized canvas mid-resize) would serialize into an
    // invalid bbox and permanently fail every locations query.
    if (east <= west || north <= south) return;
    const nextBbox = boundedWarsawViewport([west, south, east, north]);
    lastReportedViewport.current = nextBbox;
    onViewportChange(nextBbox);
  }

  return (
    <div className="map-canvas" aria-label="Interactive map of Warsaw">
      {!mapReady ? (
        <div className="map-loading" role="status">
          {loadingLabel}
        </div>
      ) : null}
      <Map
        ref={mapRef}
        initialViewState={
          initialBounds
            ? {
                bounds: [
                  [initialBounds[0], initialBounds[1]],
                  [initialBounds[2], initialBounds[3]],
                ],
                fitBoundsOptions: { padding: 32 },
              }
            : {
                longitude: 21.0122,
                latitude: 52.2297,
                zoom: 10.4,
              }
        }
        mapStyle={MAP_STYLE}
        interactiveLayerIds={["location-clusters", "locations-unclustered"]}
        onClick={(event) => void handleClick(event)}
        onMoveEnd={handleMoveEnd}
        onLoad={() => {
          mapLoaded.current = true;
          setMapReady(true);
        }}
        onError={() => {
          failureHandler.current();
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
              filter={["==", ["get", "location_id"], selectedId]}
              paint={{
                "circle-color": "transparent",
                "circle-radius": 20,
                "circle-stroke-color": "#2ea043",
                "circle-stroke-width": 3,
              }}
            />
          ) : null}
          {highlightedId && highlightedId !== selectedId ? (
            <Layer
              id="location-highlighted"
              type="circle"
              source="locations"
              filter={["==", ["get", "location_id"], highlightedId]}
              paint={{
                "circle-color": "transparent",
                "circle-radius": 16,
                "circle-stroke-color": "#4493f8",
                "circle-stroke-width": 2,
                "circle-stroke-opacity": 0.95,
              }}
            />
          ) : null}
        </Source>
      </Map>
    </div>
  );
}
