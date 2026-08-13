#!/bin/sh

set -eu

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
python3 - "$tmp_dir/root.html" "$tmp_dir/root.headers" "$release_sha" <<'PY'
import sys
from pathlib import Path

html = Path(sys.argv[1]).read_text(encoding="utf-8")
headers = Path(sys.argv[2]).read_text(encoding="utf-8").lower()
release_sha = sys.argv[3]
assert "Find a place in Warsaw" in html
assert "synthetic MVP fixtures" in html
assert "version:" in html
assert release_sha in html
assert f"x-wef-release: {release_sha}".lower() in headers
PY

printf 'Smoke: API liveness...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/live.json" \
  "$base_url/api/v1/health/live"
printf 'Smoke: API readiness...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/ready.json" \
  "$base_url/api/v1/health/ready"
python3 - "$tmp_dir/live.json" "$tmp_dir/ready.json" <<'PY'
import json
import sys
from pathlib import Path

live = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ready = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert live == {"status": "live"}
assert ready == {"status": "ready"}
PY

printf 'Smoke: grouped map projection...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/map.json" \
  "$base_url/api/v1/map/locations?bbox=20.8%2C52.1%2C21.3%2C52.4"

python3 - "$tmp_dir/map.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["type"] == "FeatureCollection"
assert payload["meta"]["feature_count"] >= 1
assert len(payload["features"]) == payload["meta"]["feature_count"]
PY

printf 'Smoke: filter facets...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/facets.json" \
  "$base_url/api/v1/filter-facets"
printf 'Smoke: selected location offers...\n'
curl_safe --fail --silent --show-error \
  --output "$tmp_dir/offers.json" \
  "$base_url/api/v1/locations/10000000-0000-4000-8000-000000000001/offers?bbox=20.8%2C52.1%2C21.3%2C52.4&include_non_matching=true&limit=20"

python3 - "$tmp_dir/facets.json" "$tmp_dir/offers.json" <<'PY'
import json
import sys
from pathlib import Path

facets = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
offers_path = Path(sys.argv[2])
offers = json.loads(offers_path.read_text(encoding="utf-8"))
assert facets["districts"]
assert facets["rooms"]
assert offers["total_count"] >= offers["matching_count"] >= 1
assert offers["items"]
assert "source_text" not in offers_path.read_text(encoding="utf-8")
PY

if [ -n "$map_style_url" ]; then
  printf 'Smoke: public map style dependency...\n'
  curl_safe --fail --silent --show-error \
    --output "$tmp_dir/map-style.json" \
    "$map_style_url"
  python3 - "$tmp_dir/map-style.json" <<'PY'
import json
import sys
from pathlib import Path

style = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert style["version"] == 8
assert style["sources"]
assert style["layers"]
PY
fi

printf 'WEF production smoke passed for release %.12s.\n' "$release_sha"
