#!/bin/sh

set -eu

if [ "$#" -ne 2 ]; then
  printf 'usage: smoke.sh BASE_URL RELEASE_SHA\n' >&2
  exit 2
fi

base_url=${1%/}
release_sha=$2
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

printf 'Smoke: web root and release marker...\n'
curl --fail --silent --show-error \
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
assert f"x-wef-release: {release_sha}".lower() in headers
PY

printf 'Smoke: API liveness...\n'
curl --fail --silent --show-error \
  --output /dev/null \
  "$base_url/api/v1/health/live"
printf 'Smoke: API readiness...\n'
curl --fail --silent --show-error \
  --output /dev/null \
  "$base_url/api/v1/health/ready"
printf 'Smoke: grouped map projection...\n'
curl --fail --silent --show-error \
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
curl --fail --silent --show-error \
  --output /dev/null \
  "$base_url/api/v1/filter-facets"
printf 'Smoke: selected location offers...\n'
curl --fail --silent --show-error \
  --output /dev/null \
  "$base_url/api/v1/locations/10000000-0000-4000-8000-000000000001/offers?bbox=20.8%2C52.1%2C21.3%2C52.4&include_non_matching=true&limit=20"

printf 'WEF production smoke passed for release %.12s.\n' "$release_sha"
