import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { FilterChipGroup } from "@/components/filter-chips";
import {
  DEFAULT_BBOX,
  DEFAULT_CONTENT_TYPES,
  DEFAULT_MAP_SEARCH_STATE,
  serializeMapSearchState,
  type MapSearchState,
} from "@/lib/map-search-params";
import { useMapNavigation } from "./use-map-navigation";

const route = vi.hoisted(() => ({ pathname: "/browse", search: "" }));
vi.mock("next/navigation", () => ({
  usePathname: () => route.pathname,
  useSearchParams: () => new URLSearchParams(route.search),
}));

const filtered: MapSearchState = {
  ...DEFAULT_MAP_SEARCH_STATE,
  bbox: "20.8,52.1,21.2,52.3",
  priceMinMinor: 100,
  priceMaxMinor: 200,
  areaMin: "30",
  areaMax: "60",
  rooms: [2],
  districts: ["wola"],
  marketTypes: ["primary"],
  contentTypes: ["unit"],
  propertyTypes: ["house"],
  publishedFrom: "2026-08-01T00:00:00.000Z",
  publishedTo: "2026-08-02T00:00:00.000Z",
};

beforeEach(() => {
  route.search = "";
  vi.spyOn(window.history, "pushState").mockImplementation(() => {});
  vi.spyOn(window.history, "replaceState").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("map URL navigation", () => {
  it("canonicalizes invalid input and leaves an already canonical URL alone", () => {
    route.search = "unknown=value";
    const { rerender } = renderHook(useMapNavigation);
    expect(window.history.replaceState).toHaveBeenCalledWith(
      null,
      "",
      "/browse",
    );
    vi.mocked(window.history.replaceState).mockClear();
    route.search = "";
    rerender();
    expect(window.history.replaceState).not.toHaveBeenCalled();
  });

  it("pushes filter changes, replaces viewport changes and ignores unchanged state", () => {
    const { result } = renderHook(useMapNavigation);
    act(() => result.current.navigate(DEFAULT_MAP_SEARCH_STATE, "push"));
    expect(window.history.pushState).not.toHaveBeenCalled();
    act(() => result.current.navigate(filtered, "push"));
    expect(window.history.pushState).toHaveBeenCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState(filtered)}`,
    );
    act(() => result.current.navigate(filtered, "replace"));
    expect(window.history.replaceState).toHaveBeenCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState(filtered)}`,
    );
  });

  it("debounces movement and cancels pending movement on navigation and unmount", () => {
    vi.useFakeTimers();
    const { result, unmount } = renderHook(useMapNavigation);
    act(() => {
      result.current.handleViewportChange("invalid");
      result.current.handleViewportChange(DEFAULT_BBOX);
      vi.advanceTimersByTime(300);
    });
    expect(window.history.replaceState).not.toHaveBeenCalled();
    act(() => {
      result.current.handleViewportChange("20.8,52.1,21.2,52.3");
      result.current.handleViewportChange("20.9,52.1,21.1,52.2");
      vi.advanceTimersByTime(299);
    });
    expect(window.history.replaceState).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(window.history.replaceState).toHaveBeenCalledOnce();
    expect(window.history.replaceState).toHaveBeenLastCalledWith(
      null,
      "",
      "/browse?bbox=20.9%2C52.1%2C21.1%2C52.2",
    );
    act(() => {
      result.current.handleViewportChange(filtered.bbox);
      result.current.navigate(filtered, "push");
      vi.advanceTimersByTime(300);
    });
    expect(window.history.replaceState).toHaveBeenCalledOnce();
    act(() => result.current.handleViewportChange(filtered.bbox));
    unmount();
    act(() => vi.advanceTimersByTime(300));
    expect(window.history.replaceState).toHaveBeenCalledOnce();
  });

  it("cancels pending movement when a back/forward URL arrives", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(useMapNavigation);
    act(() => result.current.handleViewportChange(filtered.bbox));
    route.search = serializeMapSearchState(filtered);
    rerender();
    act(() => vi.advanceTimersByTime(300));
    expect(result.current.filtersOnlySearch).not.toContain("bbox=");
    expect(window.history.replaceState).not.toHaveBeenCalled();
  });

  it.each<[FilterChipGroup, Partial<MapSearchState>]>([
    ["price", { priceMinMinor: null, priceMaxMinor: null }],
    ["area", { areaMin: null, areaMax: null }],
    ["rooms", { rooms: [] }],
    ["districts", { districts: [] }],
    ["marketTypes", { marketTypes: [] }],
    ["contentTypes", { contentTypes: DEFAULT_CONTENT_TYPES }],
    ["propertyTypes", { propertyTypes: [] }],
    ["publication", { publishedFrom: null, publishedTo: null }],
    ["quickFilter", { quickFilter: null }],
  ])("removes only the %s group", (group, cleared) => {
    const state =
      group === "quickFilter"
        ? { ...filtered, quickFilter: "last_day" }
        : filtered;
    route.search = serializeMapSearchState(state);
    const { result } = renderHook(useMapNavigation);
    const initial = result.current.searchState;
    act(() => result.current.removeFilterGroup(group));
    expect(window.history.pushState).toHaveBeenCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState({ ...initial, ...cleared })}`,
    );
  });

  it("switches presets and last-visit cutoffs while preserving unrelated filters", () => {
    route.search = serializeMapSearchState(filtered);
    const { result } = renderHook(useMapNavigation);
    act(() => result.current.toggleQuickFilter("last_day"));
    expect(window.history.pushState).toHaveBeenLastCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState({ ...filtered, quickFilter: "last_day", publishedFrom: null, publishedTo: null })}`,
    );
    act(() => result.current.toggleQuickFilter(null));
    expect(window.history.pushState).toHaveBeenCalledOnce();
    act(() => result.current.toggleLastVisit("2026-08-03T00:00:00.000Z"));
    expect(window.history.pushState).toHaveBeenLastCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState({ ...filtered, publishedFrom: "2026-08-03T00:00:00.000Z", quickFilter: null })}`,
    );
  });

  it("clears filters without moving the map and resets the map without clearing filters", () => {
    route.search = serializeMapSearchState(filtered);
    const { result } = renderHook(useMapNavigation);
    act(() => result.current.clearFiltersOnly());
    expect(window.history.pushState).toHaveBeenLastCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState({ ...DEFAULT_MAP_SEARCH_STATE, bbox: filtered.bbox })}`,
    );
    act(() => result.current.resetMapView());
    expect(window.history.pushState).toHaveBeenLastCalledWith(
      null,
      "",
      `/browse?${serializeMapSearchState({ ...filtered, bbox: DEFAULT_BBOX })}`,
    );
    act(() => result.current.navigate(DEFAULT_MAP_SEARCH_STATE, "push"));
    expect(window.history.pushState).toHaveBeenLastCalledWith(
      null,
      "",
      "/browse",
    );
  });
});
