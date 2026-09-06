import {
  mapData,
  mapMountCount,
  navigation,
  openFiltersDrawer,
  renderExplorer,
  setNavigationHref,
  setupMapExplorer,
} from "./map-explorer.test-support";

import { act, fireEvent, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import * as authApi from "@/lib/auth-api";

import * as catalogApi from "@/lib/catalog-api";

import { lastVisitStorageKeys } from "@/lib/last-visit";

import * as viewHistoryApi from "@/lib/view-history-api";

describe("map-explorer navigation", () => {
  setupMapExplorer();

  it("restores a combined URL filter query and clears to Warsaw defaults", async () => {
    navigation.search =
      "price_min=80000000&price_max=125000000&area_min=35&area_max=71.5" +
      "&rooms=2&district=wola&market_type=secondary&content_type=unit" +
      "&published_from=2026-08-01T00%3A00%3A00.000Z" +
      "&published_to=2026-08-31T23%3A59%3A59.999Z";
    renderExplorer();

    await waitFor(() => {
      expect(catalogApi.fetchLocationMap).toHaveBeenCalledWith(
        {
          bbox: catalogApi.DEFAULT_BBOX,
          price_min: 80_000_000,
          price_max: 125_000_000,
          area_min: "35",
          area_max: "71.5",
          rooms: [2],
          district: ["wola"],
          market_type: ["secondary"],
          content_type: ["unit"],
          published_from: "2026-08-01T00:00:00.000Z",
          published_to: "2026-08-31T23:59:59.999Z",
        },
        { signal: expect.any(AbortSignal) },
      );
    });

    const user = userEvent.setup();
    await openFiltersDrawer(user);
    expect(
      screen.getByRole("checkbox", { name: "roomOption:2" }),
    ).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Wola" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "clearFilters" }));
    expect(navigation.push).toHaveBeenCalledWith("/", { scroll: false });
    await waitFor(() => {
      expect(catalogApi.fetchLocationMap).toHaveBeenLastCalledWith(
        { bbox: catalogApi.DEFAULT_BBOX },
        { signal: expect.any(AbortSignal) },
      );
    });
    expect(navigation.search).toBe("");
    await openFiltersDrawer(user);
    expect(
      screen.getByRole("checkbox", { name: "roomOption:2" }),
    ).not.toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "contentType.development" }),
    ).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: "contentType.unit" }),
    ).toBeChecked();
  });

  it("debounces viewport URL replacement", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    vi.useFakeTimers();

    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(299));
    expect(navigation.replace).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "return-map" }));
    act(() => vi.advanceTimersByTime(1));
    expect(navigation.replace).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));
    expect(navigation.replace).toHaveBeenCalledWith(
      "/?bbox=20.8%2C52.1%2C21.2%2C52.3",
      { scroll: false },
    );
    expect(navigation.search).toBe("bbox=20.8%2C52.1%2C21.2%2C52.3");

    navigation.replace.mockReset();
    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  it("aborts the obsolete map request when URL state changes", async () => {
    let firstSignal: AbortSignal | undefined;
    vi.mocked(catalogApi.fetchLocationMap).mockImplementation(
      (query, options) => {
        if (query === undefined) throw new Error("expected map query");
        if (query.bbox !== catalogApi.DEFAULT_BBOX) {
          return Promise.resolve({ state: "ready", data: mapData });
        }
        return new Promise((resolve) => {
          firstSignal = options?.signal;
          options?.signal?.addEventListener(
            "abort",
            () => resolve({ state: "error" }),
            { once: true },
          );
        });
      },
    );
    renderExplorer();
    await waitFor(() => expect(firstSignal).toBeDefined());

    act(() => setNavigationHref("/?bbox=20.8%2C52.1%2C21.2%2C52.3"));

    await waitFor(() => expect(firstSignal?.aborted).toBe(true));
    expect(catalogApi.fetchLocationMap).toHaveBeenLastCalledWith(
      { bbox: "20.8,52.1,21.2,52.3" },
      { signal: expect.any(AbortSignal) },
    );
  });

  it("keeps filter drafts across viewport updates and preserves the view on apply", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    const user = userEvent.setup();
    await openFiltersDrawer(user);
    fireEvent.change(screen.getByRole("spinbutton", { name: "minimumPrice" }), {
      target: { value: "800000" },
    });
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "move-map" }));
    act(() => vi.advanceTimersByTime(300));

    expect(navigation.search).toBe("bbox=20.8%2C52.1%2C21.2%2C52.3");
    expect(
      screen.getByRole("spinbutton", { name: "minimumPrice" }),
    ).toHaveValue(800000);

    navigation.push.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "applyFilters" }));

    expect(navigation.push).toHaveBeenCalledWith(
      "/?bbox=20.8%2C52.1%2C21.2%2C52.3&price_min=80000000",
      { scroll: false },
    );
  });

  it("aborts an obsolete map request on unmount", async () => {
    let observedSignal: AbortSignal | undefined;
    vi.mocked(catalogApi.fetchLocationMap).mockImplementation(
      (_query, options) =>
        new Promise((resolve) => {
          observedSignal = options?.signal;
          options?.signal?.addEventListener(
            "abort",
            () => resolve({ state: "error" }),
            { once: true },
          );
        }),
    );

    const view = renderExplorer();
    await waitFor(() => expect(observedSignal).toBeDefined());
    view.unmount();

    expect(observedSignal?.aborted).toBe(true);
  });

  it("keeps a single map mount across viewport and filter changes", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await screen.findByTestId("map");
    expect(mapMountCount.value).toBe(1);

    await user.click(screen.getByRole("button", { name: "move-map" }));
    await waitFor(() => expect(navigation.replace).toHaveBeenCalled());
    expect(mapMountCount.value).toBe(1);

    await user.click(screen.getByRole("button", { name: "return-map" }));
    await waitFor(() =>
      expect(navigation.replace.mock.calls.length).toBeGreaterThan(1),
    );
    expect(mapMountCount.value).toBe(1);
  });

  it("exposes compact chips: quick preset toggles, applied chips remove, and the Filters drawer applies/closes", async () => {
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });
    const user = userEvent.setup();

    // Filters toggle starts collapsed with no applied groups.
    const filtersToggle = screen.getByRole("button", {
      name: /^filtersButton/,
    });
    expect(filtersToggle).toHaveAttribute("aria-haspopup", "dialog");
    expect(filtersToggle).toHaveAttribute("aria-expanded", "false");

    // Quick preset chip applies immediately through the URL lifecycle.
    await user.click(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    );
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?quick_filter=last_day",
      { scroll: false },
    );

    // Applied chips appear with values and per-group remove actions.
    navigation.search =
      "price_min=80000000&rooms=2&district=wola&quick_filter=last_day";
    for (const listener of navigation.listeners) listener();
    expect(await screen.findByText(/PLN 800,000/)).toBeInTheDocument();
    expect(filtersToggle).toHaveTextContent("4");
    await user.click(
      screen.getByRole("button", { name: "chipRemove:priceLabel" }),
    );
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?rooms=2&district=wola&quick_filter=last_day",
      { scroll: false },
    );

    // The drawer opens from the rail, applies a valid draft, and closes.
    await user.click(screen.getByRole("button", { name: "moreFilters" }));
    expect(filtersToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("heading", { name: "filtersTitle" })).toBeVisible();
    fireEvent.change(screen.getByRole("spinbutton", { name: "minimumPrice" }), {
      target: { value: "900000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "applyFilters" }));
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?price_min=90000000&rooms=2&district=wola&quick_filter=last_day",
      { scroll: false },
    );
    expect(filtersToggle).toHaveAttribute("aria-expanded", "false");
  });

  it("filters from the prior browser visit and records the current visit", async () => {
    const priorVisit = "2026-08-26T08:30:00.000Z";
    window.localStorage.setItem(lastVisitStorageKeys.last, priorVisit);
    renderExplorer();
    await screen.findByRole("button", {
      name: /Synthetic Central Residence/,
    });

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "quickFilter.since_last_visit" }),
    );

    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?published_from=2026-08-26T08%3A30%3A00.000Z",
      { scroll: false },
    );
    expect(window.localStorage.getItem(lastVisitStorageKeys.last)).not.toBe(
      priorVisit,
    );
    expect(window.sessionStorage.getItem(lastVisitStorageKeys.previous)).toBe(
      priorVisit,
    );
  });

  it("uses the authenticated account visit as the cross-device baseline", async () => {
    const localPriorVisit = "2026-08-26T08:30:00.000Z";
    const accountPriorVisit = "2026-08-25T07:15:00.000Z";
    window.localStorage.setItem(lastVisitStorageKeys.last, localPriorVisit);
    vi.mocked(authApi.fetchCurrentAccount).mockResolvedValue({
      state: "ready",
      data: {
        id: "00000000-0000-4000-8000-000000000001",
        username: "warsaw",
        role: "user",
        must_change_password: false,
        created_at: "2026-01-01T00:00:00Z",
        last_login_at: null,
      },
    });
    vi.mocked(viewHistoryApi.startAccountVisit).mockResolvedValue({
      state: "ready",
      data: {
        visit_id: "30000000-0000-4000-8000-000000000001",
        current_visit_at: "2026-08-29T08:00:00Z",
        previous_visit_at: accountPriorVisit,
      },
    });
    renderExplorer();
    await waitFor(() => {
      expect(viewHistoryApi.startAccountVisit).toHaveBeenCalledWith(
        expect.any(String),
        { signal: expect.any(AbortSignal) },
      );
      expect(
        screen.getByRole("button", {
          name: "quickFilter.since_last_visit",
        }),
      ).toBeEnabled();
    });

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "quickFilter.since_last_visit" }),
    );

    expect(navigation.push).toHaveBeenLastCalledWith(
      "/?published_from=2026-08-25T07%3A15%3A00.000Z",
      { scroll: false },
    );
  });

  it("keeps exactly one attribution surface rendered by the map control", async () => {
    renderExplorer();
    await screen.findByTestId("map");
    expect(document.querySelector(".map-attribution")).toBeNull();
  });
});
