export type BoundsLike = {
  getWest(): number;
  getSouth(): number;
  getEast(): number;
  getNorth(): number;
};

export type FocusTarget = {
  longitude: number;
  latitude: number;
  nonce: number;
};

// The pinned point may sit near the rail-facing edge of the viewport; only
// recenter when it falls clearly inside the comfortable core of the view.
const COMFORT_PADDING = 0.18;

export function isWithinComfortRegion(
  bounds: BoundsLike,
  point: [number, number],
): boolean {
  const west = bounds.getWest();
  const east = bounds.getEast();
  const south = bounds.getSouth();
  const north = bounds.getNorth();
  const longitudeSpan = Math.max(east - west, 0);
  const latitudeSpan = Math.max(north - south, 0);
  return (
    point[0] > west + longitudeSpan * COMFORT_PADDING &&
    point[0] < east - longitudeSpan * COMFORT_PADDING &&
    point[1] > south + latitudeSpan * COMFORT_PADDING &&
    point[1] < north - latitudeSpan * COMFORT_PADDING
  );
}
