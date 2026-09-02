import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountModal } from "@/components/account-modal";

const loginAccount = vi.fn();
const registerAccount = vi.fn();
const changePassword = vi.fn();
const revokeAllSessions = vi.fn();
const logoutAccount = vi.fn();
const disableOwnAccount = vi.fn();
const deleteOwnAccount = vi.fn();

vi.mock("@/lib/auth-api", () => ({
  fetchCurrentAccount: vi.fn(),
  loginAccount: (...args: unknown[]) => loginAccount(...args),
  registerAccount: (...args: unknown[]) => registerAccount(...args),
  logoutAccount: (...args: unknown[]) => logoutAccount(...args),
  changePassword: (...args: unknown[]) => changePassword(...args),
  revokeAllSessions: (...args: unknown[]) => revokeAllSessions(...args),
  disableOwnAccount: (...args: unknown[]) => disableOwnAccount(...args),
  deleteOwnAccount: (...args: unknown[]) => deleteOwnAccount(...args),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user" as const,
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

describe("AccountModal", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("validates registration fields before submit", async () => {
    const user = userEvent.setup();
    render(
      <AccountModal
        open
        account={null}
        initialMode="register"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );

    await user.click(screen.getByRole("button", { name: "registerAction" }));
    expect(await screen.findByText("usernameMin")).toBeInTheDocument();
  });

  it("logs in and reports authenticated account", async () => {
    const user = userEvent.setup();
    const onAuthenticated = vi.fn();
    loginAccount.mockResolvedValue({
      state: "ready",
      data: account,
    });

    render(
      <AccountModal
        open
        account={null}
        initialMode="login"
        onClose={() => undefined}
        onAuthenticated={onAuthenticated}
        onLoggedOut={() => undefined}
      />,
    );

    await user.type(screen.getByLabelText("usernameLabel"), "warsaw");
    await user.type(screen.getByLabelText("passwordLabel"), "longenough123");
    await user.click(screen.getByRole("button", { name: "loginAction" }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledWith(account));
  });

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

  it("surfaces username and password field limits", async () => {
    const user = userEvent.setup();
    render(
      <AccountModal
        open
        account={null}
        initialMode="register"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );

    await user.type(document.getElementById("register-username")!, "ab!");
    await user.type(document.getElementById("register-password")!, "short");
    await user.click(screen.getByRole("button", { name: "registerAction" }));
    expect(await screen.findByText("usernamePattern")).toBeInTheDocument();

    cleanup();
    render(
      <AccountModal
        open
        account={null}
        initialMode="register"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    const username = document.getElementById(
      "register-username",
    ) as HTMLInputElement;
    const password = document.getElementById(
      "register-password",
    ) as HTMLInputElement;
    username.focus();
    await user.paste("a".repeat(65));
    password.focus();
    await user.paste("p".repeat(257));
    await user.click(screen.getByRole("button", { name: "registerAction" }));
    expect(await screen.findByText("usernameMax")).toBeInTheDocument();
    expect(screen.getByText("passwordMax")).toBeInTheDocument();
  });

  it("registers, then reports the authenticated account", async () => {
    const user = userEvent.setup();
    const onAuthenticated = vi.fn();
    registerAccount.mockResolvedValue({ state: "ready", data: account });
    loginAccount.mockResolvedValue({ state: "ready", data: account });

    render(
      <AccountModal
        open
        account={null}
        initialMode="register"
        onClose={() => undefined}
        onAuthenticated={onAuthenticated}
        onLoggedOut={() => undefined}
      />,
    );

    await user.type(document.getElementById("register-username")!, "warsaw");
    await user.type(
      document.getElementById("register-password")!,
      "longenough123",
    );
    await user.type(
      document.getElementById("register-confirm-password")!,
      "longenough123",
    );
    await user.click(screen.getByRole("button", { name: "registerAction" }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledWith(account));
  });

  it("shows API failures on login and register", async () => {
    const user = userEvent.setup();
    loginAccount.mockResolvedValue({
      state: "error",
      message: "Invalid credentials.",
    });
    registerAccount.mockResolvedValue({ state: "error" });

    const loginView = render(
      <AccountModal
        open
        account={null}
        initialMode="login"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    await user.type(screen.getByLabelText("usernameLabel"), "warsaw");
    await user.type(screen.getByLabelText("passwordLabel"), "longenough123");
    await user.click(screen.getByRole("button", { name: "loginAction" }));
    expect(await screen.findByText("Invalid credentials.")).toBeInTheDocument();
    loginView.unmount();

    render(
      <AccountModal
        open
        account={null}
        initialMode="register"
        notice="saved"
        onClose={() => undefined}
        onAuthenticated={() => undefined}
        onLoggedOut={() => undefined}
      />,
    );
    expect(screen.getByText("saved")).toBeInTheDocument();
    await user.type(document.getElementById("register-username")!, "warsaw");
    await user.type(
      document.getElementById("register-password")!,
      "longenough123",
    );
    await user.type(
      document.getElementById("register-confirm-password")!,
      "otherlongenough",
    );
    await user.click(screen.getByRole("button", { name: "registerAction" }));
    expect(await screen.findByText("passwordMismatch")).toBeInTheDocument();
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

describe("AccountModal danger zone", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
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
