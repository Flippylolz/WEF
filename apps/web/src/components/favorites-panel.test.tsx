import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FavoritesPanel } from "@/components/favorites-panel";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { name?: string }) => {
    if (key === "remove" && values?.name) return `Remove ${values.name}`;
    return key;
  },
}));

afterEach(() => {
  cleanup();
});

describe("FavoritesPanel", () => {
  it("removes a starred location from the panel", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn(async () => true);
    render(
      <FavoritesPanel
        open
        loading={false}
        items={[
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ]}
        onClose={() => undefined}
        onSelect={() => undefined}
        onRemove={onRemove}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Remove Synthetic Central Residence",
      }),
    );

    await waitFor(() => {
      expect(onRemove).toHaveBeenCalledWith(
        "10000000-0000-4000-8000-000000000001",
      );
    });
  });

  it("shows loading and empty states", () => {
    const { rerender } = render(
      <FavoritesPanel
        open
        loading
        items={[]}
        onClose={() => undefined}
        onSelect={() => undefined}
        onRemove={async () => true}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("loading");

    rerender(
      <FavoritesPanel
        open
        loading={false}
        items={[]}
        onClose={() => undefined}
        onSelect={() => undefined}
        onRemove={async () => true}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("empty");
  });

  it("selects a location, reports remove failures, and closes", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onClose = vi.fn();
    const onRemove = vi.fn(async () => false);
    render(
      <FavoritesPanel
        open
        loading={false}
        items={[
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ]}
        onClose={onClose}
        onSelect={onSelect}
        onRemove={onRemove}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: /Synthetic address, Warsaw/,
      }),
    );
    expect(onSelect).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
    expect(onClose).toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", {
        name: "Remove Synthetic Central Residence",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("removeFailed");

    await user.click(screen.getByRole("button", { name: "close" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("closes from the dialog cancel event", () => {
    const onClose = vi.fn();
    render(
      <FavoritesPanel
        open
        loading={false}
        items={[]}
        onClose={onClose}
        onSelect={() => undefined}
        onRemove={async () => true}
      />,
    );
    const dialog = screen.getByRole("dialog");
    dialog.dispatchEvent(
      new Event("cancel", { bubbles: true, cancelable: true }),
    );
    expect(onClose).toHaveBeenCalled();
  });
});
