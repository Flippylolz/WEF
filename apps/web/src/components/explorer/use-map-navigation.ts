"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef } from "react";
import type { FilterChipGroup } from "@/components/filter-chips";
import {
  DEFAULT_BBOX,
  DEFAULT_CONTENT_TYPES,
  DEFAULT_MAP_SEARCH_STATE,
  normalizeBbox,
  parseMapSearchParams,
  serializeMapSearchState,
  toMapLocationQuery,
  type MapSearchState,
} from "@/lib/map-search-params";

export function useMapNavigation() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawSearch = searchParams.toString();
  const searchState = useMemo(
    () => parseMapSearchParams(new URLSearchParams(rawSearch)),
    [rawSearch],
  );
  const canonicalSearch = useMemo(
    () => serializeMapSearchState(searchState),
    [searchState],
  );
  const mapQueryParams = useMemo(
    () => toMapLocationQuery(searchState),
    [searchState],
  );
  const filtersOnlySearch = useMemo(() => {
    const params = new URLSearchParams(canonicalSearch);
    params.delete("bbox");
    return params.toString();
  }, [canonicalSearch]);
  const viewportTimer = useRef<number | null>(null);
  const cancelViewportUpdate = useCallback(() => {
    if (viewportTimer.current !== null) {
      window.clearTimeout(viewportTimer.current);
      viewportTimer.current = null;
    }
  }, []);

  useEffect(() => {
    cancelViewportUpdate();
    if (rawSearch !== canonicalSearch) {
      router.replace(href(pathname, canonicalSearch), { scroll: false });
    }
  }, [cancelViewportUpdate, canonicalSearch, pathname, rawSearch, router]);

  useEffect(() => {
    return cancelViewportUpdate;
  }, [cancelViewportUpdate]);

  const navigate = useCallback(
    (nextState: MapSearchState, mode: "push" | "replace") => {
      cancelViewportUpdate();
      const nextSearch = serializeMapSearchState(nextState);
      if (nextSearch === canonicalSearch) return;
      router[mode](href(pathname, nextSearch), { scroll: false });
    },
    [cancelViewportUpdate, canonicalSearch, pathname, router],
  );

  const handleViewportChange = useCallback(
    (bbox: string) => {
      const normalized = normalizeBbox(bbox);
      cancelViewportUpdate();
      if (normalized === null || normalized === searchState.bbox) return;
      viewportTimer.current = window.setTimeout(() => {
        viewportTimer.current = null;
        navigate({ ...searchState, bbox: normalized }, "replace");
      }, 300);
    },
    [cancelViewportUpdate, navigate, searchState],
  );

  const removeFilterGroup = useCallback(
    (group: FilterChipGroup) => {
      const next = { ...searchState };
      if (group === "price") {
        next.priceMinMinor = null;
        next.priceMaxMinor = null;
      } else if (group === "area") {
        next.areaMin = null;
        next.areaMax = null;
      } else if (group === "rooms") {
        next.rooms = [];
      } else if (group === "districts") {
        next.districts = [];
      } else if (group === "marketTypes") {
        next.marketTypes = [];
      } else if (group === "contentTypes") {
        next.contentTypes = DEFAULT_CONTENT_TYPES;
      } else if (group === "propertyTypes") {
        next.propertyTypes = [];
      } else if (group === "publication") {
        next.publishedFrom = null;
        next.publishedTo = null;
      } else if (group === "quickFilter") {
        next.quickFilter = null;
      }
      navigate(next, "push");
    },
    [navigate, searchState],
  );

  const toggleQuickFilter = useCallback(
    (presetId: string | null) => {
      navigate(
        {
          ...searchState,
          quickFilter: presetId,
          publishedFrom: presetId ? null : searchState.publishedFrom,
        },
        "push",
      );
    },
    [navigate, searchState],
  );

  const toggleLastVisit = useCallback(
    (publishedFrom: string | null) => {
      navigate(
        {
          ...searchState,
          publishedFrom,
          quickFilter: null,
        },
        "push",
      );
    },
    [navigate, searchState],
  );

  function clearFiltersOnly() {
    navigate(
      {
        ...DEFAULT_MAP_SEARCH_STATE,
        bbox: searchState.bbox,
      },
      "push",
    );
  }

  function resetMapView() {
    navigate({ ...searchState, bbox: DEFAULT_BBOX }, "push");
  }

  return {
    searchState,
    canonicalSearch,
    mapQueryParams,
    filtersOnlySearch,
    navigate,
    handleViewportChange,
    removeFilterGroup,
    toggleQuickFilter,
    toggleLastVisit,
    clearFiltersOnly,
    resetMapView,
  };
}

function href(pathname: string, search: string) {
  return search ? `${pathname}?${search}` : pathname;
}
