import {
  detail,
  renderDrawer,
  setupOfferDetailDrawer,
} from "./offer-detail-drawer.test-support";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { useState } from "react";

import { describe, expect, it, vi } from "vitest";

import { OfferDetailDrawer } from "@/components/offer-detail-drawer";

import * as catalogApi from "@/lib/catalog-api";

describe("offer-detail-drawer lifecycle", () => {
  setupOfferDetailDrawer();

  it("exposes a single close control to assistive technology", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer();

    await screen.findByText("development · primary");
    const scrim = screen
      .getByTestId("offer-detail-overlay")
      .querySelector(".offer-detail-scrim");
    expect(scrim).not.toBeNull();
    expect(scrim).toHaveAttribute("aria-hidden", "true");
    expect(scrim).toHaveAttribute("tabindex", "-1");
    expect(screen.getAllByRole("button", { name: "detailClose" })).toHaveLength(
      1,
    );
  });

  it("announces not-found without leaking payloads", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "not_found",
    });
    renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "detailNotFound",
    );
  });

  it("closes from escape and restores focus to the trigger", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();

    function ClosableDrawer() {
      const [open, setOpen] = useState(true);
      return (
        <OfferDetailDrawer
          open={open}
          offerId={detail.id}
          matchesFilters={false}
          detailQuery={
            {
              data: detail,
              error: null,
              isError: false,
              isPending: false,
              isSuccess: true,
            } as never
          }
          account={null}
          onClose={() => setOpen(false)}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: trigger }}
        />
      );
    }

    render(<ClosableDrawer />);
    await userEvent.keyboard("{Escape}");
    await waitFor(() =>
      expect(
        screen.queryByTestId("offer-detail-overlay"),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("shows loading and error states for the detail query", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const pending = render(
      <QueryClientProvider client={queryClient}>
        <OfferDetailDrawer
          open
          offerId={detail.id}
          matchesFilters
          detailQuery={
            {
              data: undefined,
              error: null,
              isError: false,
              isPending: true,
              isSuccess: false,
            } as never
          }
          account={null}
          onClose={() => undefined}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: document.createElement("button") }}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("detailLoading");
    pending.unmount();

    render(
      <QueryClientProvider client={queryClient}>
        <OfferDetailDrawer
          open
          offerId={detail.id}
          matchesFilters
          detailQuery={
            {
              data: undefined,
              error: new Error("boom"),
              isError: true,
              isPending: false,
              isSuccess: false,
            } as never
          }
          account={null}
          onClose={() => undefined}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: document.createElement("button") }}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("detailError");
  });
});
