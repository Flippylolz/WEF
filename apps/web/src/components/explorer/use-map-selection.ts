"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { LocationMapFeature, ViewportListing } from "@/lib/catalog-api";
import type { FocusTarget } from "@/lib/listing-focus";
type MobilePanelMode = "map" | "sheet" | "full";

export function useMapSelection(
  features: LocationMapFeature[] | undefined,
  isMobile: boolean,
  onAnnounceSelection: (name: string) => void,
) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [selectedOfferMatchesFilters, setSelectedOfferMatchesFilters] =
    useState<boolean | null>(null);
  const [selectedListingId, setSelectedListingId] = useState<string | null>(
    null,
  );
  const [focusTarget, setFocusTarget] = useState<FocusTarget | null>(null);
  const offerTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [selectedFeatureSnapshot, setSelectedFeatureSnapshot] =
    useState<LocationMapFeature | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobilePanelMode, setMobilePanelMode] =
    useState<MobilePanelMode>("map");
  const [highlightedLocationId, setHighlightedLocationId] = useState<
    string | null
  >(null);
  const resultsPanelRef = useRef<HTMLElement | null>(null);
  const resultsScrollRef = useRef<number>(0);
  const resultsTriggerRef = useRef<HTMLButtonElement | null>(null);
  const resultsRestorationNonce = selectedId === null ? 1 : 0;
  useEffect(() => {
    if (selectedId !== null) return;
    if (resultsScrollRef.current === 0 && resultsTriggerRef.current === null) {
      return;
    }
    const panel = resultsPanelRef.current;
    if (panel !== null) {
      panel.scrollTop = resultsScrollRef.current;
    }
    resultsTriggerRef.current?.focus();
    resultsScrollRef.current = 0;
    resultsTriggerRef.current = null;
    // The nonce marks the transition back into the results list.
  }, [resultsRestorationNonce, selectedId]);
  const panelOpen = isMobile ? mobilePanelMode !== "map" : sidebarOpen;

  function openMobileSheet() {
    setMobilePanelMode("sheet");
  }

  function openMobileFullList() {
    setMobilePanelMode("full");
  }

  function closeMobilePanel() {
    setMobilePanelMode("map");
  }

  const selectedFeature = useMemo(() => {
    if (selectedId === null) return null;
    return (
      features?.find((feature) => feature.id === selectedId) ??
      selectedFeatureSnapshot
    );
  }, [features, selectedFeatureSnapshot, selectedId]);

  function selectLocation(locationId: string) {
    const currentFeature = features?.find(
      (feature) => feature.id === locationId,
    );
    if (currentFeature) {
      setSelectedFeatureSnapshot(currentFeature);
      onAnnounceSelection(currentFeature.properties.display_name);
    }
    if (selectedId === null) {
      resultsScrollRef.current =
        resultsPanelRef.current?.scrollTop ?? resultsScrollRef.current;
    }
    setSelectedId(locationId);
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
    if (isMobile) {
      openMobileSheet();
    } else {
      setSidebarOpen(true);
    }
  }

  function selectListing(listing: ViewportListing, trigger: HTMLButtonElement) {
    resultsTriggerRef.current = trigger;
    setSelectedListingId(listing.id);
    setFocusTarget({
      longitude: listing.location.geometry.coordinates[0],
      latitude: listing.location.geometry.coordinates[1],
      nonce: Date.now(),
    });
    selectLocation(listing.location.id);
  }

  function backToResults() {
    setSelectedId(null);
    setSelectedListingId(null);
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
    if (isMobile) {
      setMobilePanelMode("full");
    }
  }

  function selectOffer(
    offerId: string,
    matchesFilters: boolean,
    trigger: HTMLButtonElement,
  ) {
    offerTriggerRef.current = trigger;
    setSelectedOfferId(offerId);
    setSelectedOfferMatchesFilters(matchesFilters);
  }

  function closeOfferDetail() {
    setSelectedOfferId(null);
    setSelectedOfferMatchesFilters(null);
  }

  return {
    selectedId,
    selectedOfferId,
    selectedOfferMatchesFilters,
    selectedListingId,
    focusTarget,
    offerTriggerRef,
    sidebarOpen,
    setSidebarOpen,
    mobilePanelMode,
    highlightedLocationId,
    setHighlightedLocationId,
    resultsPanelRef,
    panelOpen,
    openMobileSheet,
    openMobileFullList,
    closeMobilePanel,
    selectLocation,
    selectListing,
    backToResults,
    selectOffer,
    closeOfferDetail,
    selectedFeature,
  };
}
