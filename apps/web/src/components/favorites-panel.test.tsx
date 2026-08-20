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
});
