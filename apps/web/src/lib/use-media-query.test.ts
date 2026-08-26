import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useMediaQuery, usePrefersReducedMotion } from "@/lib/use-media-query";

describe("useMediaQuery", () => {
  it("tracks matchMedia changes", async () => {
    const listeners = new Set<(event: MediaQueryListEvent) => void>();
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("56rem"),
        media: query,
        addEventListener: (
          _: string,
          listener: (event: MediaQueryListEvent) => void,
        ) => {
          listeners.add(listener);
        },
        removeEventListener: (
          _: string,
          listener: (event: MediaQueryListEvent) => void,
        ) => {
          listeners.delete(listener);
        },
      })),
    );

    const { result } = renderHook(() => useMediaQuery("(max-width: 56rem)"));
    await waitFor(() => expect(result.current).toBe(true));
    vi.unstubAllGlobals();
  });

  it("tracks reduced-motion preference", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("prefers-reduced-motion"),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      })),
    );

    const { result } = renderHook(() => usePrefersReducedMotion());
    await waitFor(() => expect(result.current).toBe(true));
    vi.unstubAllGlobals();
  });
});
