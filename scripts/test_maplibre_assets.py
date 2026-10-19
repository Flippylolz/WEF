"""Regression coverage for both MapLibre worker distribution layouts."""

# ruff: noqa: D101, D102, PT027

from __future__ import annotations

import unittest

from scripts.deploy.maplibre_assets import MapLibreAssetsError, validate_maplibre_assets

JAVASCRIPT_HEADERS = "HTTP/1.1 200 OK\r\nContent-Type: application/javascript; charset=utf-8\r\n"
SPLIT_WORKER = 'import {Worker} from "./maplibre-gl-shared.mjs"; new Worker(self);'
BUNDLED_WORKER = 'self.addEventListener("message", event => self.postMessage(event.data));'
SHARED_MODULE = "export {};"


class MapLibreAssetsTests(unittest.TestCase):
    def test_accepts_split_module_worker(self) -> None:
        validate_maplibre_assets(JAVASCRIPT_HEADERS, SPLIT_WORKER, SHARED_MODULE)

    def test_accepts_bundled_message_worker(self) -> None:
        validate_maplibre_assets(JAVASCRIPT_HEADERS, BUNDLED_WORKER, SHARED_MODULE)

    def test_accepts_onmessage_worker(self) -> None:
        validate_maplibre_assets(
            JAVASCRIPT_HEADERS,
            "self.onmessage = event => self.postMessage(event.data);",
            SHARED_MODULE,
        )

    def test_accepts_empty_shared_stub_when_worker_is_self_contained(self) -> None:
        validate_maplibre_assets(JAVASCRIPT_HEADERS, BUNDLED_WORKER, "")

    def test_rejects_html_shared_stub_even_for_bundled_worker(self) -> None:
        with self.assertRaises(MapLibreAssetsError):
            validate_maplibre_assets(JAVASCRIPT_HEADERS, BUNDLED_WORKER, "<!doctype html>")

    def test_rejects_html_and_non_worker_responses(self) -> None:
        for worker in ("<!doctype html><html>Not found</html>", "", "export const unrelated = 1;"):
            with self.subTest(worker=worker), self.assertRaises(MapLibreAssetsError):
                validate_maplibre_assets(JAVASCRIPT_HEADERS, worker, SHARED_MODULE)

    def test_rejects_imported_shared_fallback_or_missing_exports(self) -> None:
        for shared in ("<!doctype html><html>Not found</html>", "", "const unrelated = 1;"):
            with self.subTest(shared=shared), self.assertRaises(MapLibreAssetsError):
                validate_maplibre_assets(JAVASCRIPT_HEADERS, SPLIT_WORKER, shared)

    def test_rejects_non_javascript_mime_despite_misleading_other_header(self) -> None:
        headers = "Content-Type: text/html\r\nX-Note: javascript\r\n"
        with self.assertRaises(MapLibreAssetsError):
            validate_maplibre_assets(headers, BUNDLED_WORKER, SHARED_MODULE)


if __name__ == "__main__":
    unittest.main()
