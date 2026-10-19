import {
  account,
  changePassword,
  logoutAccount,
  setupAccountModal,
} from "./account-modal.test-support";

import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import { AccountModal } from "@/components/account-modal";

describe("account-modal password", () => {
  setupAccountModal();

  it("forces password change when must_change_password is set", async () => {
    render(
      <AccountModal
        open
        account={{ ...account, must_change_password: true }}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );

    expect(screen.getByText("forcedPasswordTitle")).toBeInTheDocument();
    expect(screen.getByLabelText("currentPasswordLabel")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "revokeSessionsAction" }),
    ).not.toBeInTheDocument();
  });

  it("changes password and reports logout", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    const onNotice = vi.fn();
    changePassword.mockResolvedValue({ state: "ready", data: null });

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
      within(dialog).getByRole("button", { name: "changePasswordAction" }),
    );
    const current = dialog.querySelector(
      "#current-password",
    ) as HTMLInputElement;
    const next = dialog.querySelector("#new-password") as HTMLInputElement;
    const confirm = dialog.querySelector(
      "#confirm-new-password",
    ) as HTMLInputElement;
    await user.type(current, "longenough123");
    await user.type(next, "newlongenough456");
    await user.type(confirm, "newlongenough456");
    await user.click(
      within(dialog).getByRole("button", { name: "changePasswordAction" }),
    );

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith({
        current_password: "longenough123",
        new_password: "newlongenough456",
      });
      expect(onNotice).toHaveBeenCalledWith("passwordChangedNotice");
      expect(onLoggedOut).toHaveBeenCalled();
    });
  });

  it("returns to the signed-in panel when password change is cancelled", async () => {
    const user = userEvent.setup();
    render(
      <AccountModal
        open
        account={account}
        initialMode="account"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "changePasswordAction" }),
    );
    expect(
      screen.getByRole("button", { name: "backToAccountAction" }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "backToAccountAction" }),
    );
    expect(screen.getByText("signedInTitle")).toBeInTheDocument();
  });

  it("logs out from the password panel and ignores a closed dialog", async () => {
    const user = userEvent.setup();
    const onLoggedOut = vi.fn();
    const onClose = vi.fn();
    logoutAccount.mockResolvedValue({ state: "ready", data: null });

    render(
      <AccountModal
        open
        account={account}
        initialMode="password"
        onClose={onClose}
        onAuthenticated={() => undefined}
        onLoggedOut={onLoggedOut}
      />,
    );
    expect(screen.getByText("changePasswordTitle")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "logoutAction" }));
    await waitFor(() => expect(onLoggedOut).toHaveBeenCalled());

    cleanup();
    render(
      <AccountModal
        open={false}
        account={null}
        initialMode="login"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("surfaces a password-change API failure", async () => {
    const user = userEvent.setup();
    changePassword.mockResolvedValue({ state: "error" });
    render(
      <AccountModal
        open
        account={account}
        initialMode="password"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );

    await user.type(
      document.getElementById("current-password")!,
      "longenough123",
    );
    await user.type(
      document.getElementById("new-password")!,
      "newlongenough456",
    );
    await user.type(
      document.getElementById("confirm-new-password")!,
      "newlongenough456",
    );
    await user.click(
      screen.getByRole("button", { name: "changePasswordAction" }),
    );
    expect(await screen.findByText("changePasswordFailed")).toBeInTheDocument();
  });
});
