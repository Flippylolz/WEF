import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AccountModal } from "@/components/account-modal";

const loginAccount = vi.fn();

vi.mock("@/lib/auth-api", () => ({
  fetchCurrentAccount: vi.fn(),
  loginAccount: (...args: unknown[]) => loginAccount(...args),
  registerAccount: vi.fn(),
  logoutAccount: vi.fn(),
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

    await waitFor(() =>
      expect(onAuthenticated).toHaveBeenCalledWith(account),
    );
  });
});
