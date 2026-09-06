import {
  listingPage,
  renderExplorer,
  setupMapExplorer,
} from "./map-explorer.test-support";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import * as catalogApi from "@/lib/catalog-api";

const source = listingPage.items[0]!;
const item: catalogApi.UnmappedListing = {
  ...source,
  location: {
    id: source.location.id,
    display_name: "Synthetic uncertain",
    display_address: "District only",
    district: source.location.district,
    confidence: "low",
    coordinate_precision: "district",
    location_accuracy: {
      precision: "area",
      validation_status: "accepted",
      uncertainty_reason: "area_only",
      label: "Approximate area",
    },
  },
};
const page: catalogApi.UnmappedListingPage = {
  items: [item],
  matching_count: 2,
  mapped_matching_count: 1,
  next_cursor: "u1.next",
  filter_scope: "non_spatial",
};

describe("uncertain location discovery", () => {
  setupMapExplorer();
  it("paginates independently and opens detail without selecting a map location", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.fetchUnmappedListings).mockImplementation(
      async (query) => ({
        state: "ready",
        data: query.cursor
          ? {
              ...page,
              items: [{ ...item, id: "20000000-0000-4000-8000-000000000010" }],
              next_cursor: null,
            }
          : page,
      }),
    );
    const detail = vi
      .spyOn(catalogApi, "fetchOfferDetail")
      .mockResolvedValue({ state: "not_found" });
    renderExplorer();
    await user.click(await screen.findByText("uncertainTitle (2)"));
    expect(screen.getByText("uncertainScope")).toBeVisible();
    expect(await screen.findByText("Approximate area")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "loadMore" }));
    await waitFor(() =>
      expect(
        screen.getAllByRole("button", { name: /Synthetic uncertain/ }),
      ).toHaveLength(2),
    );
    expect(catalogApi.fetchUnmappedListings).toHaveBeenLastCalledWith(
      expect.objectContaining({ cursor: "u1.next" }),
      expect.anything(),
    );
    const trigger = screen.getAllByRole("button", {
      name: /Synthetic uncertain/,
    })[0]!;
    await user.click(trigger);
    await waitFor(() =>
      expect(detail).toHaveBeenCalledWith(item.id, expect.anything()),
    );
    expect(catalogApi.fetchLocationOffers).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: "detailClose", hidden: false }),
    );
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("recovers a discovery failure and reports an empty non-spatial result", async () => {
    const user = userEvent.setup();
    vi.mocked(catalogApi.fetchUnmappedListings)
      .mockResolvedValueOnce({ state: "error" })
      .mockResolvedValue({
        state: "ready",
        data: { ...page, items: [], matching_count: 0, next_cursor: null },
      });
    renderExplorer();
    await user.click(await screen.findByText("uncertainTitle"));
    expect(await screen.findByText("uncertainError")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "retry" }));
    expect(await screen.findByText("uncertainEmpty")).toBeVisible();
  });
});
