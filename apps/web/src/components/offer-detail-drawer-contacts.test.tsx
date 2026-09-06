import {
  detail,
  renderDrawer,
  setupOfferDetailDrawer,
  signedInAccount,
} from "./offer-detail-drawer.test-support";

import { axe } from "vitest-axe";
import { screen } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import * as catalogApi from "@/lib/catalog-api";

import * as contactsApi from "@/lib/contacts-api";

describe("offer-detail-drawer contacts", () => {
  setupOfferDetailDrawer();

  it("keeps the contact prompt accessible with keyboard activation", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    const onRequestSignIn = vi.fn();
    const { container } = renderDrawer(detail.id, { onRequestSignIn });
    const button = await screen.findByRole("button", {
      name: "detailRevealSignInAction",
    });
    expect((await axe(container)).violations).toHaveLength(0);
    button.focus();
    await userEvent.keyboard("{Enter}");
    expect(onRequestSignIn).toHaveBeenCalledOnce();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
  });

  it("asks anonymous users to sign in instead of revealing", async () => {
    const onRequestSignIn = vi.fn();
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer(detail.id, { onRequestSignIn });

    expect(
      await screen.findByText("detailRevealSignInRequired"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealSignInAction" }),
    );
    expect(onRequestSignIn).toHaveBeenCalled();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
  });

  it("blocks reveal until forced password change completes", async () => {
    const onRequestPasswordChange = vi.fn();
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer(detail.id, {
      account: { ...signedInAccount, must_change_password: true },
      onRequestPasswordChange,
    });

    expect(
      await screen.findByText("detailRevealPasswordRequired"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealPasswordAction" }),
    );
    expect(onRequestPasswordChange).toHaveBeenCalled();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
  });

  it("reveals contacts only after an explicit click", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    vi.mocked(contactsApi.revealOfferContacts).mockResolvedValue({
      state: "ready",
      data: {
        contacts: [
          {
            kind: "phone",
            value: "+48111222333",
            masked_value: "+48***333",
          },
        ],
      },
    });
    renderDrawer(detail.id, { account: signedInAccount });

    expect(
      await screen.findByRole("button", { name: "detailRevealContacts" }),
    ).toBeInTheDocument();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
    expect(screen.queryByText("+48111222333")).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );

    expect(await screen.findByText("+48111222333")).toBeInTheDocument();
    expect(contactsApi.revealOfferContacts).toHaveBeenCalledWith(detail.id);
  });

  it("shows rate-limit and unavailable errors from reveal", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    vi.mocked(contactsApi.revealOfferContacts)
      .mockResolvedValueOnce({
        state: "error",
        code: "rate_limited",
      })
      .mockResolvedValueOnce({
        state: "error",
        code: "unavailable",
      })
      .mockResolvedValueOnce({
        state: "error",
        code: "forbidden",
      })
      .mockResolvedValueOnce({
        state: "error",
      });
    renderDrawer(detail.id, { account: signedInAccount });

    const reveal = await screen.findByRole("button", {
      name: "detailRevealContacts",
    });
    await userEvent.click(reveal);
    expect(
      await screen.findByText("detailRevealError.rate_limited"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.unavailable"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.forbidden"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.unknown"),
    ).toBeInTheDocument();
  });

  it("shows empty revealed contacts and a date-only source fallback", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: {
        ...detail,
        verified_source_url: null,
        source_message_id: null,
        source_history: [
          {
            source_message_id: "50000000-0000-4000-8000-000000000002",
            relationship: "edit",
            published_at: "2026-08-01T10:00:00Z",
            edited_at: "2026-08-02T10:00:00Z",
          },
        ],
      },
    });
    vi.mocked(contactsApi.revealOfferContacts).mockResolvedValue({
      state: "ready",
      data: { contacts: [] },
    });
    renderDrawer(detail.id, { account: signedInAccount });

    expect(
      await screen.findByText(/detailSourceFallback:/),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(await screen.findByText("detailRevealEmpty")).toBeInTheDocument();
  });
});
