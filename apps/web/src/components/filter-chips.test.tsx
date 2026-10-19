import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AppliedFilterChips,
  countAppliedGroups,
} from "@/components/filter-chips";
import { DEFAULT_MAP_SEARCH_STATE } from "@/lib/map-search-params";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: Record<string, string | number>) => {
      if (values && Object.keys(values).length > 0) {
        const suffix = Object.entries(values)
          .map(([name, value]) => `${name}=${value}`)
          .join("|");
        return `${key}[${suffix}]`;
      }
      return key;
    },
}));

const quickFilters = [{ id: "last_day", label_key: "quickFilter.last_day" }];

function renderChips(
  overrides: Partial<Parameters<typeof AppliedFilterChips>[0]>,
) {
  const props = {
    state: DEFAULT_MAP_SEARCH_STATE,
    quickFilters,
    quickFiltersLoading: false,
    lastVisitAt: null,
    onRemoveGroup: vi.fn(),
    onToggleQuickFilter: vi.fn(),
    onToggleLastVisit: vi.fn(),
    onOpenFilters: vi.fn(),
    ...overrides,
  };
  render(<AppliedFilterChips {...props} />);
  return props;
}

describe("AppliedFilterChips", () => {
  afterEach(cleanup);

  it("renders no applied chips and no count for the default state", () => {
    renderChips({});
    expect(countAppliedGroups(DEFAULT_MAP_SEARCH_STATE)).toBe(0);
    expect(screen.getByRole("button", { name: "moreFilters" })).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /^chipRemove/ }),
    ).not.toBeInTheDocument();
  });

  it("summarizes every applied group with a concise value", () => {
    renderChips({
      state: {
        ...DEFAULT_MAP_SEARCH_STATE,
        priceMinMinor: 80_000_000,
        priceMaxMinor: 125_000_000,
        areaMin: "35",
        rooms: [2, 3],
        districts: ["wola", "mokotow", "ochota"],
        marketTypes: ["secondary"],
        contentTypes: ["unit"],
        propertyTypes: ["house", "apartment"],
        publishedFrom: "2026-08-01T00:00:00.000Z",
      },
    });

    expect(countAppliedGroups({ ...DEFAULT_MAP_SEARCH_STATE })).toBe(0);
    expect(
      countAppliedGroups({
        ...DEFAULT_MAP_SEARCH_STATE,
        propertyTypes: ["house"],
      }),
    ).toBe(1);
    expect(screen.getByText("PLN 800,000 – PLN 1,250,000")).toBeInTheDocument();
    expect(screen.getByText("≥ 35 m²")).toBeInTheDocument();
    expect(screen.getByText("roomsLabel")).toBeInTheDocument();
    expect(screen.getByText(/rooms=2, 3\|count=2/)).toBeInTheDocument();
    expect(
      screen.getByText(/values=Wola, Mokotow\|count=3/),
    ).toBeInTheDocument();
    expect(screen.getByText("marketType.secondary")).toBeInTheDocument();
    expect(screen.getByText("contentType.unit")).toBeInTheDocument();
    expect(
      screen.getByText("propertyType.house, propertyType.apartment"),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 Aug 2026/)).toBeInTheDocument();
  });

  it("labels the active quick preset as an applied chip and toggles it off", async () => {
    const user = userEvent.setup();
    const props = renderChips({
      state: { ...DEFAULT_MAP_SEARCH_STATE, quickFilter: "last_day" },
    });

    const active = screen.getByRole("button", {
      name: "quickFilter.last_day",
    });
    expect(active).toHaveAttribute("aria-pressed", "true");

    await user.click(active);
    expect(props.onToggleQuickFilter).toHaveBeenCalledWith(null);
  });

  it("applies the previous visit cutoff and toggles it off", async () => {
    const user = userEvent.setup();
    const lastVisitAt = "2026-08-26T08:30:00.000Z";
    const props = renderChips({ lastVisitAt });

    const filter = screen.getByRole("button", {
      name: "quickFilter.since_last_visit",
    });
    expect(filter).toHaveAttribute("aria-pressed", "false");
    await user.click(filter);
    expect(props.onToggleLastVisit).toHaveBeenCalledWith(lastVisitAt);

    cleanup();
    const activeProps = renderChips({
      lastVisitAt,
      state: { ...DEFAULT_MAP_SEARCH_STATE, publishedFrom: lastVisitAt },
    });
    const active = screen.getByRole("button", {
      name: "quickFilter.since_last_visit",
    });
    expect(active).toHaveAttribute("aria-pressed", "true");
    await user.click(active);
    expect(activeProps.onToggleLastVisit).toHaveBeenCalledWith(null);
  });

  it("disables the last-visit shortcut until a baseline exists", () => {
    renderChips({ lastVisitAt: null });
    expect(
      screen.getByRole("button", {
        name: /quickFilter.since_last_visit.*since_last_visit_unavailable/,
      }),
    ).toBeDisabled();
  });

  it("removes exactly the requested group and opens the drawer from the rail", async () => {
    const user = userEvent.setup();
    const props = renderChips({
      state: {
        ...DEFAULT_MAP_SEARCH_STATE,
        priceMinMinor: 80_000_000,
        rooms: [2],
      },
    });

    await user.click(
      screen.getByRole("button", { name: "chipRemove[label=priceLabel]" }),
    );
    expect(props.onRemoveGroup).toHaveBeenCalledWith("price");
    expect(props.onRemoveGroup).not.toHaveBeenCalledWith("rooms");

    await user.click(screen.getByRole("button", { name: "moreFilters" }));
    expect(props.onOpenFilters).toHaveBeenCalledOnce();
  });

  it("shows a loading status while quick filters load", () => {
    renderChips({ quickFiltersLoading: true });
    expect(screen.getByRole("status")).toHaveTextContent("quickFiltersLoading");
  });

  it("formats a district pair without an overflow summary", () => {
    renderChips({
      state: { ...DEFAULT_MAP_SEARCH_STATE, districts: ["wola", "mokotow"] },
    });
    expect(screen.getByText("Wola, Mokotow")).toBeInTheDocument();
  });

  it("counts every applied group", () => {
    expect(
      countAppliedGroups({
        ...DEFAULT_MAP_SEARCH_STATE,
        priceMaxMinor: 200,
        areaMax: "60",
        rooms: [2],
        districts: ["wola"],
        marketTypes: ["primary"],
        contentTypes: ["unit"],
        propertyTypes: ["house"],
        publishedTo: "2026-08-02T00:00:00Z",
        quickFilter: "last_day",
      }),
    ).toBe(9);
  });

  it("renders upper bounds and a publication cutoff", () => {
    renderChips({
      state: {
        ...DEFAULT_MAP_SEARCH_STATE,
        priceMaxMinor: 80_000_000,
        areaMax: "60",
        publishedTo: "2026-08-02T00:00:00Z",
      },
    });
    expect(screen.getByText("≤ PLN 800,000")).toBeVisible();
    expect(screen.getByText("≤ 60 m²")).toBeVisible();
    expect(screen.getByText("chip.publicationTo[to=2 Aug 2026]")).toBeVisible();
  });

  it("renders bounded area and publication ranges", () => {
    renderChips({
      state: {
        ...DEFAULT_MAP_SEARCH_STATE,
        areaMin: "30",
        areaMax: "60",
        publishedFrom: "2026-08-01T00:00:00Z",
        publishedTo: "2026-08-02T00:00:00Z",
      },
    });
    expect(screen.getByText("30 – 60 m²")).toBeVisible();
    expect(
      screen.getByText("chip.publicationRange[from=1 Aug 2026|to=2 Aug 2026]"),
    ).toBeVisible();
  });

  it("hides unavailable presets and ignores a stale preset id", () => {
    renderChips({
      quickFilters: [],
      lastVisitAt: undefined,
      state: { ...DEFAULT_MAP_SEARCH_STATE, quickFilter: "removed" },
    });
    expect(
      screen.queryByLabelText("quickFiltersLabel"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^chipRemove/ }),
    ).not.toBeInTheDocument();
  });

  it("shows presets while the browser visit baseline is still unavailable", () => {
    renderChips({ lastVisitAt: undefined });
    expect(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "quickFilter.since_last_visit" }),
    ).not.toBeInTheDocument();
  });

  it("removes the applied preset chip", async () => {
    const props = renderChips({
      state: { ...DEFAULT_MAP_SEARCH_STATE, quickFilter: "last_day" },
    });
    await userEvent.click(
      screen.getByRole("button", {
        name: "chipRemove[label=quickFilter.last_day]",
      }),
    );
    expect(props.onToggleQuickFilter).toHaveBeenCalledWith(null);
  });
});
