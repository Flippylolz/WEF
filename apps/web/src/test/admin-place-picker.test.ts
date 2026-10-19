import { afterEach, beforeEach, expect, test, vi } from "vitest";

const listeners = vi.fn();

beforeEach(() => {
  document.body.innerHTML = "";
  vi.resetModules();
  listeners.mockReset();
  vi.spyOn(window, "addEventListener").mockImplementation(listeners);
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

async function start(data: Record<string, string> = {}, omit: string[] = []) {
  document.body.innerHTML = `
    <div id="map"></div><span id="marker"></span><span id="ghost"></span>
    <input id="lat-input"><input id="lng-input">
    <button id="zoom-in">+</button><button id="zoom-out">-</button>
    <p id="tile-error" hidden>Tiles unavailable</p>`;
  const map = document.getElementById("map")!;
  Object.assign(map.dataset, { lat: "52.23", lon: "21.01", ...data });
  Object.defineProperties(map, {
    clientWidth: { value: 512, configurable: true },
    clientHeight: { value: 512, configurable: true },
    setPointerCapture: { value: vi.fn(), configurable: true },
  });
  vi.spyOn(map, "getBoundingClientRect").mockReturnValue({
    left: 10,
    top: 20,
    width: 512,
    height: 512,
    x: 10,
    y: 20,
    right: 522,
    bottom: 532,
    toJSON: () => ({}),
  });
  for (const id of omit) document.getElementById(id)?.remove();
  // @ts-expect-error The backend asset intentionally exposes no module API.
  await import("../../../backend/src/wef_backend/features/admin/interface/statics/place_picker.js");
  return map;
}

const lat = () => document.querySelector<HTMLInputElement>("#lat-input")!;
const lon = () => document.querySelector<HTMLInputElement>("#lng-input")!;
const pin = () => document.getElementById("marker")!;
const tile = () => document.querySelector<HTMLImageElement>("#map img")!;
function pointer(map: HTMLElement, type: string, x = 266, y = 276, button = 0) {
  const event = new MouseEvent(type, { clientX: x, clientY: y, button });
  Object.defineProperty(event, "pointerId", { value: 1 });
  map.dispatchEvent(event);
}

test("pages without a map install no interaction handlers", async () => {
  // @ts-expect-error The backend asset intentionally exposes no module API.
  await import("../../../backend/src/wef_backend/features/admin/interface/statics/place_picker.js");
  expect(listeners).not.toHaveBeenCalled();
});

test("empty source coordinates render tiles and hide both pins", async () => {
  await start();
  expect(tile().src).toContain("/15/");
  expect(pin().hidden).toBe(true);
  expect(document.getElementById("ghost")!.hidden).toBe(true);
});

test.each([
  { pointLat: "", pointLon: "21", candidateLat: "", candidateLon: "21" },
  { pointLat: "bad", pointLon: "21", candidateLat: "52", candidateLon: "bad" },
])("invalid coordinate pairs never place a pin: %j", async (data) => {
  await start(data);
  expect(pin().hidden).toBe(true);
  expect(document.getElementById("ghost")!.hidden).toBe(true);
});

test("a candidate fills empty coordinates and retains its ghost", async () => {
  await start({ candidateLat: "52.23", candidateLon: "21.01" });
  expect(lat().value).toBe("52.230000");
  expect(lon().value).toBe("21.010000");
  expect(pin().hidden).toBe(false);
  expect(document.getElementById("ghost")!.hidden).toBe(false);
});

test("an existing point renders independently of the candidate", async () => {
  await start({
    pointLat: "52.23",
    pointLon: "21.01",
    candidateLat: "52.2301",
    candidateLon: "21.0101",
  });
  expect(pin().hidden).toBe(false);
  expect(pin().style.left).toBe("256px");
});

test.each(["marker", "ghost", "lat-input", "lng-input", "zoom-in", "zoom-out"])(
  "optional %s may be absent",
  async (id) => {
    await start({ candidateLat: "52.23", candidateLon: "21.01" }, [id]);
    expect(tile()).toBeTruthy();
  },
);

test.each([
  { pointLat: "52.23", pointLon: "20.9" },
  { pointLat: "52.33", pointLon: "21.01" },
  { pointLat: "52.23", pointLon: "21.11" },
  { pointLat: "52.13", pointLon: "21.01" },
])("offscreen points are hidden: %j", async (data) => {
  await start(data);
  expect(pin().hidden).toBe(true);
});

test("a left-button click stores the clicked coordinate", async () => {
  const map = await start();
  pointer(map, "pointerdown");
  pointer(map, "pointerup");
  expect(lat().value).toBe("52.230000");
  expect(lon().value).toBe("21.010000");
  expect(map.setPointerCapture).toHaveBeenCalledWith(1);
});

test("unclaimed pointers and other buttons leave inputs untouched", async () => {
  const map = await start();
  pointer(map, "pointermove");
  pointer(map, "pointerup");
  pointer(map, "pointerdown", 266, 276, 1);
  pointer(map, "pointerup");
  expect(lat().value).toBe("");
  expect(map.setPointerCapture).not.toHaveBeenCalled();
});

test("a small motion still selects while dragging only pans", async () => {
  const map = await start();
  pointer(map, "pointerdown");
  pointer(map, "pointermove", 267, 277);
  pointer(map, "pointerup", 267, 277);
  const selected = lat().value;
  pointer(map, "pointerdown");
  pointer(map, "pointermove", 366, 376);
  pointer(map, "pointerup", 366, 376);
  expect(lat().value).toBe(selected);
});

test("buttons, wheel and double-click update zoom without retaining stale tiles", async () => {
  const map = await start();
  const old = tile();
  document.getElementById("zoom-in")!.click();
  expect(tile().src).toContain("/16/");
  expect(old.isConnected).toBe(false);
  document.getElementById("zoom-out")!.click();
  expect(tile().src).toContain("/15/");
  map.dispatchEvent(new WheelEvent("wheel", { deltaY: -1, cancelable: true }));
  expect(tile().src).toContain("/16/");
  map.dispatchEvent(new WheelEvent("wheel", { deltaY: 1, cancelable: true }));
  map.dispatchEvent(new MouseEvent("dblclick"));
  expect(tile().src).toContain("/16/");
});

test.each(["3", "19"])("zoom is clamped at %s", async (zoom) => {
  const map = await start({ zoom });
  if (zoom === "3") document.getElementById("zoom-out")!.click();
  else map.dispatchEvent(new MouseEvent("dblclick"));
  expect(tile().src).toContain(`/${zoom}/`);
});

test("valid input changes recenter and malformed values preserve the current pin", async () => {
  await start();
  lat().value = "52.24";
  lon().value = "21.02";
  lat().dispatchEvent(new Event("change"));
  expect(pin().style.left).toBe("256px");
  expect(lon().value).toBe("21.020000");
  lat().value = "bad";
  lat().dispatchEvent(new Event("change"));
  lat().value = "52.24";
  lon().value = "bad";
  lon().dispatchEvent(new Event("change"));
  expect(pin().style.left).toBe("256px");
});

test.each(["lat-input", "lng-input"])(
  "partial form with missing %s cannot sync",
  async (id) => {
    await start({}, [id]);
    const remaining = document.querySelector<HTMLInputElement>("input")!;
    remaining.value = "52";
    remaining.dispatchEvent(new Event("change"));
    expect(pin().hidden).toBe(true);
  },
);

test.each([false, true])(
  "tile failures expose an optional warning: %s",
  async (missing) => {
    await start({}, missing ? ["tile-error"] : []);
    tile().dispatchEvent(new Event("error"));
    if (!missing)
      expect(document.getElementById("tile-error")!.hidden).toBe(false);
  },
);

test("resize reuses visible tiles and wraps longitudes around the world", async () => {
  const map = await start({ zoom: "3", lon: "-179", lat: "0" });
  expect(
    [...map.querySelectorAll<HTMLImageElement>("img")].some((image) =>
      image.src.includes("/3/7/"),
    ),
  ).toBe(true);
  Object.defineProperty(map, "clientWidth", { value: 768, configurable: true });
  const resize = listeners.mock.calls.find(([name]) => name === "resize")![1];
  resize(new Event("resize"));
  expect(map.querySelectorAll("img").length).toBeGreaterThan(0);
});
