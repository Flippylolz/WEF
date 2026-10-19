#!/bin/sh
set -eu
mkdir -p tmp
# A missing base is a failed prerequisite, never an implicit comparison with ourselves.
git show "${CONTRACT_BASE_REF:-origin/main}:contracts/openapi/v1.json" > tmp/openapi-base.json
image='tufin/oasdiff:v1.34.0@sha256:dd742562c1f3146f6e2a80bc01951cc87d15a249ac2aca05665339e30cf03620'
docker run --rm -v "$PWD:/work" "$image" breaking --fail-on ERR /work/tmp/openapi-base.json /work/contracts/openapi/v1.json
python3 -c 'import json; d=json.load(open("contracts/openapi/v1.json")); del d["paths"]["/api/v1/map/locations"]; json.dump(d,open("tmp/openapi-breaking-probe.json","w"))'
trap 'rm -f tmp/openapi-breaking-probe.json' EXIT
status=0
docker run --rm -v "$PWD:/work" "$image" breaking --fail-on ERR /work/contracts/openapi/v1.json /work/tmp/openapi-breaking-probe.json || status=$?
if [ "$status" -ne 1 ]; then
    echo "oasdiff negative probe returned unexpected status $status (expected breaking-change rejection)" >&2
    exit 1
fi
