import {
  account,
  loginAccount,
  registerAccount,
  setupAccountModal,
} from "./account-modal.test-support";

import { axe } from "vitest-axe";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { describe, expect, it, vi } from "vitest";

import { AccountModal } from "@/components/account-modal";

describe("account-modal credentials", () => {
  setupAccountModal();

  it("keeps credential controls accessible and submits from the keyboard", async () => {
    const user = userEvent.setup();
    const onAuthenticated = vi.fn();
    loginAccount.mockResolvedValue({ state: "ready", data: account });
    const { container } = render(
      <AccountModal
        open
        account={null}
        initialMode="login"
        onClose={() => undefined}
        onAuthenticated={onAuthenticated}
        onLoggedOut={() => undefined}
      />,
    );
    expect((await axe(container)).violations).toHaveLength(0);
    screen.getByLabelText("usernameLabel").focus();
    await user.keyboard("warsaw{Tab}longenough123{Enter}");
    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledWith(account));
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

  it.each([
    ["register", "server detail"],
    ["register", undefined],
    ["login", "server detail"],
    ["login", undefined],
  ])(
    "shows %s failure after a valid registration submission (%s)",
    async (stage, message) => {
      registerAccount.mockResolvedValue(
        stage === "register"
          ? { state: "error", message }
          : { state: "ready", data: account },
      );
      loginAccount.mockResolvedValue({ state: "error", message });
      const onAuthenticated = vi.fn();
      render(
        <AccountModal
          open
          account={null}
          initialMode="register"
          onClose={vi.fn()}
          onAuthenticated={onAuthenticated}
          onLoggedOut={vi.fn()}
        />,
      );
      fireEvent.change(document.getElementById("register-username")!, {
        target: { value: "warsaw" },
      });
      fireEvent.change(document.getElementById("register-password")!, {
        target: { value: "longenough123" },
      });
      fireEvent.change(document.getElementById("register-confirm-password")!, {
        target: { value: "longenough123" },
      });
      await userEvent.click(
        screen.getByRole("button", { name: "registerAction" }),
      );
      expect(await screen.findByRole("alert")).toHaveTextContent(
        message ??
          (stage === "register"
            ? "registerFailed"
            : "loginAfterRegisterFailed"),
      );
      expect(onAuthenticated).not.toHaveBeenCalled();
    },
  );

  it("shows the fallback for login failures without a problem detail", async () => {
    loginAccount.mockResolvedValue({ state: "error" });
    render(
      <AccountModal
        open
        account={null}
        initialMode="login"
        onClose={vi.fn()}
        onAuthenticated={vi.fn()}
        onLoggedOut={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("usernameLabel"), {
      target: { value: "warsaw" },
    });
    fireEvent.change(screen.getByLabelText("passwordLabel"), {
      target: { value: "longenough123" },
    });
    await userEvent.click(screen.getByRole("button", { name: "loginAction" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("loginFailed");
  });

  it("allows cancelling the account dialog without submitting a form", () => {
    const onClose = vi.fn();
    render(
      <AccountModal
        open
        account={null}
        initialMode="login"
        onClose={onClose}
        onAuthenticated={vi.fn()}
        onLoggedOut={vi.fn()}
      />,
    );
    const event = new Event("cancel", { bubbles: true, cancelable: true });
    fireEvent(screen.getByRole("dialog"), event);
    expect(event.defaultPrevented).toBe(true);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
