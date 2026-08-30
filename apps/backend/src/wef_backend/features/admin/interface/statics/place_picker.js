/* Minimal click-to-place slippy map for the owner location console.
 * Renders OSM raster tiles with drag panning and integer zoom;
 * clicking the map drops the pin and fills the lat/lng inputs. */
(function () {
  "use strict";

  var TILE = 256;
  var MIN_ZOOM = 3;
  var MAX_ZOOM = 19;

  var map = document.getElementById("map");
  if (!map) return;
  var marker = document.getElementById("marker");
  var ghost = document.getElementById("ghost");
  var latInput = document.getElementById("lat-input");
  var lngInput = document.getElementById("lng-input");

  var zoom = parseInt(map.dataset.zoom || "15", 10);
  var center = worldPoint(parseFloat(map.dataset.lon), parseFloat(map.dataset.lat));
  var point = readPair(map.dataset.pointLat, map.dataset.pointLon);
  var candidate = readPair(map.dataset.candidateLat, map.dataset.candidateLon);
  var tiles = {};
  var drag = null;
  var tileFailures = 0;

  function readPair(rawLat, rawLon) {
    if (rawLat === undefined || rawLat === null || rawLat === "") return null;
    var lat = parseFloat(rawLat);
    var lon = parseFloat(rawLon);
    if (isNaN(lat) || isNaN(lon)) return null;
    return { lat: lat, lon: lon };
  }

  function lonToWorld(lon, z) {
    return ((lon + 180) / 360) * Math.pow(2, z);
  }

  function latToWorld(lat, z) {
    var s = Math.sin((lat * Math.PI) / 180);
    return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * Math.pow(2, z);
  }

  function worldToLon(x, z) {
    return (x / Math.pow(2, z)) * 360 - 180;
  }

  function worldToLat(y, z) {
    var n = Math.PI - (2 * Math.PI * y) / Math.pow(2, z);
    return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  }

  function worldPoint(lon, lat) {
    return { x: lonToWorld(lon, zoom), y: latToWorld(lat, zoom) };
  }

  function tileUrl(x, y) {
    var n = Math.pow(2, zoom);
    var wrapped = ((x % n) + n) % n;
    return "https://tile.openstreetmap.org/" + zoom + "/" + wrapped + "/" + y + ".png";
  }

  function viewBounds() {
    var width = map.clientWidth;
    var height = map.clientHeight;
    return {
      left: center.x - width / (2 * TILE),
      top: center.y - height / (2 * TILE),
      columns: width / TILE,
      rows: height / TILE,
    };
  }

  function render() {
    var bounds = viewBounds();
    var maxTile = Math.pow(2, zoom);
    var keep = {};
    var x;
    var y;
    for (x = Math.floor(bounds.left); x <= Math.floor(bounds.left + bounds.columns); x++) {
      for (y = Math.max(0, Math.floor(bounds.top)); y <= Math.min(maxTile - 1, Math.floor(bounds.top + bounds.rows)); y++) {
        var key = x + "/" + y;
        keep[key] = true;
        var img = tiles[key];
        if (!img) {
          img = document.createElement("img");
          img.src = tileUrl(x, y);
          img.alt = "";
          img.decoding = "async";
          img.draggable = false;
          img.addEventListener("error", function () {
            tileFailures += 1;
            var notice = document.getElementById("tile-error");
            if (notice) notice.hidden = false;
          });
          map.appendChild(img);
          tiles[key] = img;
        }
        img.style.left = Math.round((x - bounds.left) * TILE) + "px";
        img.style.top = Math.round((y - bounds.top) * TILE) + "px";
      }
    }
    for (var stale in tiles) {
      if (!keep[stale]) {
        tiles[stale].remove();
        delete tiles[stale];
      }
    }
    positionPin(marker, point);
    positionPin(ghost, candidate);
  }

  function positionPin(pin, coords) {
    if (!pin) return;
    if (!coords) {
      pin.hidden = true;
      return;
    }
    var bounds = viewBounds();
    var left = (lonToWorld(coords.lon, zoom) - bounds.left) * TILE;
    var top = (latToWorld(coords.lat, zoom) - bounds.top) * TILE;
    if (left < -20 || top < -20 || left > map.clientWidth + 20 || top > map.clientHeight + 20) {
      pin.hidden = true;
      return;
    }
    pin.hidden = false;
    pin.style.left = Math.round(left) + "px";
    pin.style.top = Math.round(top) + "px";
  }

  function setPoint(lat, lon, recenter) {
    point = { lat: lat, lon: lon };
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lon.toFixed(6);
    if (recenter) center = worldPoint(lon, lat);
    render();
  }

  function setZoom(next) {
    var clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next));
    if (clamped === zoom) return;
    var anchor = { lat: worldToLat(center.y, zoom), lon: worldToLon(center.x, zoom) };
    zoom = clamped;
    center = worldPoint(anchor.lon, anchor.lat);
    render();
  }

  function eventPixel(event) {
    var rect = map.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  map.addEventListener("pointerdown", function (event) {
    if (event.button !== 0) return;
    var start = eventPixel(event);
    drag = { start: start, origin: { x: center.x, y: center.y }, moved: false };
    map.setPointerCapture(event.pointerId);
  });

  map.addEventListener("pointermove", function (event) {
    if (!drag) return;
    var current = eventPixel(event);
    var dx = current.x - drag.start.x;
    var dy = current.y - drag.start.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
    center = { x: drag.origin.x - dx / TILE, y: drag.origin.y - dy / TILE };
    render();
  });

  map.addEventListener("pointerup", function (event) {
    if (!drag) return;
    var moved = drag.moved;
    drag = null;
    if (moved) return;
    var pixel = eventPixel(event);
    var bounds = viewBounds();
    var lon = worldToLon(bounds.left + pixel.x / TILE, zoom);
    var lat = worldToLat(bounds.top + pixel.y / TILE, zoom);
    setPoint(lat, lon, false);
  });

  map.addEventListener("wheel", function (event) {
    event.preventDefault();
    setZoom(zoom + (event.deltaY < 0 ? 1 : -1));
  }, { passive: false });

  map.addEventListener("dblclick", function () {
    setZoom(zoom + 1);
  });

  var zoomIn = document.getElementById("zoom-in");
  var zoomOut = document.getElementById("zoom-out");
  if (zoomIn) zoomIn.addEventListener("click", function () { setZoom(zoom + 1); });
  if (zoomOut) zoomOut.addEventListener("click", function () { setZoom(zoom - 1); });

  function syncFromInputs() {
    var lat = parseFloat(latInput && latInput.value);
    var lon = parseFloat(lngInput && lngInput.value);
    if (isNaN(lat) || isNaN(lon)) return;
    setPoint(lat, lon, true);
  }

  if (latInput) latInput.addEventListener("change", syncFromInputs);
  if (lngInput) lngInput.addEventListener("change", syncFromInputs);

  window.addEventListener("resize", render);

  if (point === null && candidate !== null) {
    setPoint(candidate.lat, candidate.lon, false);
  } else {
    render();
  }
})();
