import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { QuickFilterBar } from "@/components/quick-filter-bar";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

describe("QuickFilterBar", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows a loading status before presets arrive", () => {
    render(
      <QuickFilterBar
        presets={[]}
        selectedId={null}
        loading
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("quickFiltersLoading");
  });

  it("renders nothing when there are no presets", () => {
    const { container } = render(
      <QuickFilterBar
        presets={[]}
        selectedId={null}
        onSelect={() => undefined}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("toggles the selected preset off when it is clicked again", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <QuickFilterBar
        presets={[{ id: "last_day", label_key: "quickFilter.last_day" }]}
        selectedId="last_day"
        onSelect={onSelect}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "quickFilter.last_day" }),
    );
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
