import {
  account,
  deleteOwnAccount,
  disableOwnAccount,
  logoutAccount,
  revokeAllSessions,
  setupAccountModal,
} from "./account-modal.test-support";

import { render, screen, waitFor, within } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import { AccountModal } from "@/components/account-modal";

describe("account-modal sessions", () => {
  setupAccountModal();

  it("revokes all sessions and reports logout", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    const onNotice = vi.fn();
    revokeAllSessions.mockResolvedValue({ state: "ready", data: null });

    render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
        onNotice={onNotice}
      />,
    );

    const dialog = screen.getByRole("dialog");
    await user.click(
      within(dialog).getByRole("button", { name: "revokeSessionsAction" }),
    );

    await waitFor(() => {
      expect(revokeAllSessions).toHaveBeenCalled();
      expect(onNotice).toHaveBeenCalledWith("sessionsRevokedNotice");
      expect(onLoggedOut).toHaveBeenCalled();
    });
  });

  it("keeps the signed-in panel open when logout fails", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    logoutAccount.mockResolvedValue({ state: "error" });
    render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
      />,
    );
    await user.click(screen.getByRole("button", { name: "logoutAction" }));
    expect(onLoggedOut).not.toHaveBeenCalled();
    expect(screen.getByText("signedInTitle")).toBeInTheDocument();
  });

  it("keeps the signed-in panel open when session revoke fails", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    revokeAllSessions
      .mockResolvedValueOnce({ state: "error", message: "blocked" })
      .mockResolvedValueOnce({ state: "error" });
    render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "revokeSessionsAction" }),
    );
    expect(await screen.findByText("blocked")).toBeInTheDocument();
    expect(onLoggedOut).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "revokeSessionsAction" }),
    );
    expect(await screen.findByText("revokeSessionsFailed")).toBeInTheDocument();
  });

  it("disables the account after explicit confirmation", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    const onNotice = vi.fn();
    const onClose = vi.fn();
    disableOwnAccount.mockResolvedValue({ state: "ready", data: null });

    const view = render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={onClose}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
        onNotice={onNotice}
      />,
    );
    const dialog = view.container.querySelector("dialog")!;
    await user.click(
      within(dialog).getByRole("button", { name: "disableAction" }),
    );
    expect(
      within(dialog).getByRole("button", { name: "disableConfirmAction" }),
    ).toBeInTheDocument();
    await user.click(
      within(dialog).getByRole("button", { name: "disableConfirmAction" }),
    );

    await waitFor(() => {
      expect(disableOwnAccount).toHaveBeenCalledTimes(1);
      expect(deleteOwnAccount).not.toHaveBeenCalled();
      expect(onNotice).toHaveBeenCalledWith("disabledNotice");
      expect(onLoggedOut).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("deletes the account after explicit confirmation", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    deleteOwnAccount.mockResolvedValue({ state: "ready", data: null });

    const view = render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
      />,
    );
    const dialog = view.container.querySelector("dialog")!;
    await user.click(
      within(dialog).getByRole("button", { name: "deleteAction" }),
    );
    await user.click(
      within(dialog).getByRole("button", { name: "deleteConfirmAction" }),
    );

    await waitFor(() => {
      expect(deleteOwnAccount).toHaveBeenCalledTimes(1);
      expect(disableOwnAccount).not.toHaveBeenCalled();
      expect(onLoggedOut).toHaveBeenCalled();
    });
  });

  it("reports failures and stays in the confirm step", async () => {
    const user = userEvent.setup();
    deleteOwnAccount.mockResolvedValue({
      state: "error",
      message: "problem detail",
    });

    const view = render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    const dialog = view.container.querySelector("dialog")!;
    await user.click(
      within(dialog).getByRole("button", { name: "deleteAction" }),
    );
    await user.click(
      within(dialog).getByRole("button", { name: "deleteConfirmAction" }),
    );

    await waitFor(() => {
      expect(within(dialog).getByRole("alert")).toHaveTextContent(
        "problem detail",
      );
    });
    expect(
      within(dialog).getByRole("button", { name: "deleteConfirmAction" }),
    ).toBeInTheDocument();
    await user.click(
      within(dialog).getByRole("button", { name: "cancelAction" }),
    );
    expect(
      within(dialog).getByRole("button", { name: "deleteAction" }),
    ).toBeInTheDocument();
  });
});
