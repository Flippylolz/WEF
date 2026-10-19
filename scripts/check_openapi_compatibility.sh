#!/bin/sh
set -eu
mkdir -p tmp
# A missing base is a failed prerequisite, never an implicit comparison with ourselves.
git show "${CONTRACT_BASE_REF:-origin/main}:contracts/openapi/v1.json" > tmp/openapi-base.json
image='tufin/oasdiff:v1.28.0@sha256:86830f988eaafcf589acb2794ee5ab78e3300ded071d6517bf085469300cbf36'
docker run --rm -v "$PWD:/work" "$image" breaking --fail-on ERR /work/tmp/openapi-base.json /work/contracts/openapi/v1.json
python3 -c 'import json; d=json.load(open("contracts/openapi/v1.json")); del d["paths"]["/api/v1/map/locations"]; json.dump(d,open("tmp/openapi-breaking-probe.json","w"))'
trap 'rm -f tmp/openapi-breaking-probe.json' EXIT
status=0
docker run --rm -v "$PWD:/work" "$image" breaking --fail-on ERR /work/contracts/openapi/v1.json /work/tmp/openapi-breaking-probe.json || status=$?
if [ "$status" -ne 1 ]; then
    echo "oasdiff negative probe returned unexpected status $status (expected breaking-change rejection)" >&2
    exit 1
fi
