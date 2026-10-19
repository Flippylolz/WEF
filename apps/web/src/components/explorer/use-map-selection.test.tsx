import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useMapSelection } from "./use-map-selection";

afterEach(cleanup);

it("retains selection while features are unavailable and restores the mobile result panel", () => {
  const announce = vi.fn();
  const { result, rerender } = renderHook(
    ({ available }) =>
      useMapSelection(available ? [] : undefined, true, announce),
    { initialProps: { available: true } },
  );
  act(() => result.current.selectLocation("pending"));
  expect(result.current.selectedFeature).toBeNull();
  expect(result.current.mobilePanelMode).toBe("sheet");
  expect(result.current.panelOpen).toBe(true);
  expect(announce).not.toHaveBeenCalled();
  rerender({ available: false });
  act(() => result.current.selectLocation("another"));
  expect(result.current.selectedId).toBe("another");
  act(() => result.current.backToResults());
  expect(result.current.mobilePanelMode).toBe("full");
  act(() => result.current.closeMobilePanel());
  expect(result.current.panelOpen).toBe(false);
  const panel = document.createElement("section");
  panel.scrollTop = 75;
  result.current.resultsPanelRef.current = panel;
  act(() => result.current.selectLocation("pending"));
  panel.scrollTop = 0;
  act(() => result.current.backToResults());
  expect(panel.scrollTop).toBe(75);
  act(() => result.current.selectLocation("pending"));
  result.current.resultsPanelRef.current = null;
  act(() => result.current.backToResults());
  expect(result.current.selectedId).toBeNull();
});

it("retains the replacement opener when catalog refreshes during offer detail", () => {
  const { result } = renderHook(() =>
    useMapSelection(undefined, false, vi.fn()),
  );
  const original = document.createElement("button");
  const replacement = document.createElement("button");
  act(() => result.current.selectOffer("offer-1", true, original));
  act(() => {
    result.current.registerOfferTrigger("offer-2", replacement);
    result.current.registerOfferTrigger("offer-1", null);
  });
  expect(result.current.offerTriggerRef.current).toBe(original);
  act(() => result.current.registerOfferTrigger("offer-1", replacement));
  act(() => result.current.closeOfferDetail());
  expect(result.current.offerTriggerRef.current).toBe(replacement);
});
