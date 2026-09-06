import { act, renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useMapSelection } from "./use-map-selection";

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
