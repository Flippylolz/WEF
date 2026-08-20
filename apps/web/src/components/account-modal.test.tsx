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
const changePassword = vi.fn();
const revokeAllSessions = vi.fn();
const logoutAccount = vi.fn();

vi.mock("@/lib/auth-api", () => ({
  fetchCurrentAccount: vi.fn(),
  loginAccount: (...args: unknown[]) => loginAccount(...args),
  registerAccount: vi.fn(),
  logoutAccount: (...args: unknown[]) => logoutAccount(...args),
  changePassword: (...args: unknown[]) => changePassword(...args),
  revokeAllSessions: (...args: unknown[]) => revokeAllSessions(...args),
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
});
