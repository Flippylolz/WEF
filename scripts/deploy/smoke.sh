#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  printf 'usage: smoke.sh BASE_URL RELEASE_SHA [MAP_STYLE_URL]\n' >&2
  exit 2
fi

base_url=${1%/}
release_sha=$2
map_style_url=${3:-}
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

curl_safe() {
  curl --connect-timeout 10 --max-time 30 "$@"
}

printf 'Smoke: web root and release marker...\n'
curl_safe --fail --silent --show-error \
  --dump-header "$tmp_dir/root.headers" \
  --output "$tmp_dir/root.html" \
  "$base_url/"
python3 "$SCRIPT_DIR/smoke_contracts.py" root \
  "$tmp_dir/root.html" "$tmp_dir/root.headers" "$release_sha"

printf 'Smoke: API liveness...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/live.json" \
  "$base_url/api/v1/health/live"
printf 'Smoke: API readiness...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/ready.json" \
  "$base_url/api/v1/health/ready"
python3 "$SCRIPT_DIR/smoke_contracts.py" health \
  "$tmp_dir/live.json" "$tmp_dir/ready.json"

printf 'Smoke: grouped map projection...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/map.json" \
  "$base_url/api/v1/map/locations?bbox=20.8%2C52.1%2C21.3%2C52.4"

python3 "$SCRIPT_DIR/smoke_contracts.py" map \
  "$tmp_dir/map.json" "$tmp_dir/location_id"
location_id=$(cat "$tmp_dir/location_id")

printf 'Smoke: Warsaw district boundaries...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/districts.json" \
  "$base_url/data/warsaw-districts.geojson"
python3 "$SCRIPT_DIR/smoke_contracts.py" districts \
  "$tmp_dir/districts.json"

printf 'Smoke: MapLibre module worker...\n'
curl_safe --fail --silent --show-error \
  --dump-header "$tmp_dir/maplibre-worker.headers" \
  --output "$tmp_dir/maplibre-worker.mjs" \
  "$base_url/vendor/maplibre/maplibre-gl-worker.mjs"
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/maplibre-shared.mjs" \
  "$base_url/vendor/maplibre/maplibre-gl-shared.mjs"
python3 "$SCRIPT_DIR/maplibre_assets.py" \
  "$tmp_dir/maplibre-worker.headers" \
  "$tmp_dir/maplibre-worker.mjs" \
  "$tmp_dir/maplibre-shared.mjs"

printf 'Smoke: filter facets...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/facets.json" \
  "$base_url/api/v1/filter-facets"
printf 'Smoke: selected location offers...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/offers.json" \
  "$base_url/api/v1/locations/${location_id}/offers?bbox=20.8%2C52.1%2C21.3%2C52.4&include_non_matching=true&limit=20"

python3 "$SCRIPT_DIR/smoke_contracts.py" offers \
  "$tmp_dir/facets.json" "$tmp_dir/offers.json"

if [ -n "$map_style_url" ]; then
  printf 'Smoke: public map style dependency...\n'
  curl_safe --fail --silent --show-error \
    --output "$tmp_dir/map-style.json" \
    "$map_style_url"
  python3 "$SCRIPT_DIR/smoke_contracts.py" style \
    "$tmp_dir/map-style.json"
fi

printf 'WEF production smoke passed for release %.12s.\n' "$release_sha"
