import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserToolbar } from "@/components/user-toolbar";
import * as authApi from "@/lib/auth-api";
import * as favoritesApi from "@/lib/favorites-api";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { name?: string }) => {
    if (key === "remove" && values?.name) return `Remove ${values.name}`;
    return key;
  },
}));

const account: authApi.Account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user",
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

function renderToolbar(
  props: {
    onSelectFavorite?: (locationId: string) => void;
    onRegisterAuthOpener?: (open: (intent: { mode: "login" }) => void) => void;
    onAccountChange?: (account: authApi.Account | null) => void;
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <UserToolbar {...props} />
    </QueryClientProvider>,
  );
}

describe("UserToolbar", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("opens login and register from the anonymous toolbar", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: null,
    });
    renderToolbar();

    await user.click(
      await screen.findByRole("button", { name: "loginAction" }),
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "close" }));

    await user.click(screen.getByRole("button", { name: "registerAction" }));
    expect(screen.getByText("registerTitle")).toBeInTheDocument();
  });

  it("registers an external auth opener", async () => {
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: null,
    });
    let openAuth:
      ((intent: { mode: "login" | "register" }) => void) | undefined;
    renderToolbar({
      onRegisterAuthOpener: (open) => {
        openAuth = open;
      },
    });

    await screen.findByRole("button", { name: "loginAction" });
    openAuth?.({ mode: "register" });
    expect(await screen.findByText("registerTitle")).toBeInTheDocument();
  });

  it("shows the signed-in username and opens favorites", async () => {
    const user = userEvent.setup();
    const onSelectFavorite = vi.fn();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: account,
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: {
        items: [
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ],
      },
    });
    renderToolbar({ onSelectFavorite });

    expect(
      await screen.findByRole("button", { name: "warsaw" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "openList" }));
    await user.click(
      await screen.findByRole("button", {
        name: /Synthetic address, Warsaw/,
      }),
    );
    expect(onSelectFavorite).toHaveBeenCalledWith(
      "10000000-0000-4000-8000-000000000001",
    );
  });

  it("hides favorites while a forced password change is required", async () => {
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: { ...account, must_change_password: true },
    });
    renderToolbar();

    expect(
      await screen.findByRole("button", { name: "warsaw" }),
    ).toBeInTheDocument();
    expect(screen.getByText("forcedPasswordTitle")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "openList" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the password modal open when login requires a password change", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: null,
    });
    vi.spyOn(authApi, "loginAccount").mockResolvedValue({
      state: "ready",
      data: { ...account, must_change_password: true },
    });
    renderToolbar();

    await user.click(
      within(await screen.findByLabelText("toolbarLabel")).getByRole("button", {
        name: "loginAction",
      }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("usernameLabel"), "warsaw");
    await user.type(
      within(dialog).getByLabelText("passwordLabel"),
      "longenough123",
    );
    await user.click(
      within(dialog).getByRole("button", { name: "loginAction" }),
    );
    expect(await screen.findByText("forcedPasswordTitle")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "close" }));
    expect(
      document.querySelector(".account-modal:not(.favorites-panel)"),
    ).not.toHaveAttribute("open");
  });

  it("removes a favorite from the panel", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: account,
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: {
        items: [
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ],
      },
    });
    vi.spyOn(favoritesApi, "removeFavorite").mockResolvedValue({
      state: "ready",
      data: null,
    });
    renderToolbar();

    await user.click(await screen.findByRole("button", { name: "openList" }));
    await user.click(
      screen.getByRole("button", {
        name: "Remove Synthetic Central Residence",
      }),
    );
    await waitFor(() => {
      expect(favoritesApi.removeFavorite).toHaveBeenCalledWith(
        "10000000-0000-4000-8000-000000000001",
      );
    });
  });

  it("keeps a favorite when removal fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: account,
    });
    vi.spyOn(favoritesApi, "fetchFavorites").mockResolvedValue({
      state: "ready",
      data: {
        items: [
          {
            location_id: "10000000-0000-4000-8000-000000000001",
            display_name: "Synthetic Central Residence",
            display_address: "Synthetic address, Warsaw",
            district: "srodmiescie",
            created_at: "2026-08-20T12:00:00+00:00",
          },
        ],
      },
    });
    vi.spyOn(favoritesApi, "removeFavorite").mockResolvedValue({
      state: "error",
    });
    renderToolbar();

    await user.click(await screen.findByRole("button", { name: "openList" }));
    await user.click(
      screen.getByRole("button", {
        name: "Remove Synthetic Central Residence",
      }),
    );
    await waitFor(() => {
      expect(favoritesApi.removeFavorite).toHaveBeenCalledWith(
        "10000000-0000-4000-8000-000000000001",
      );
    });
  });

  it("notifies when authentication completes or logs out", async () => {
    const user = userEvent.setup();
    const onAccountChange = vi.fn();
    vi.spyOn(authApi, "fetchCurrentAccount").mockResolvedValue({
      state: "ready",
      data: null,
    });
    vi.spyOn(authApi, "loginAccount").mockResolvedValue({
      state: "ready",
      data: account,
    });
    vi.spyOn(authApi, "logoutAccount").mockResolvedValue({
      state: "ready",
      data: null,
    });
    renderToolbar({ onAccountChange });

    await user.click(
      within(await screen.findByLabelText("toolbarLabel")).getByRole("button", {
        name: "loginAction",
      }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("usernameLabel"), "warsaw");
    await user.type(
      within(dialog).getByLabelText("passwordLabel"),
      "longenough123",
    );
    await user.click(
      within(dialog).getByRole("button", { name: "loginAction" }),
    );

    await waitFor(() => expect(onAccountChange).toHaveBeenCalledWith(account));

    await user.click(screen.getByRole("button", { name: "warsaw" }));
    await user.click(screen.getByRole("button", { name: "logoutAction" }));
    await waitFor(() => expect(onAccountChange).toHaveBeenCalledWith(null));
  });
});
