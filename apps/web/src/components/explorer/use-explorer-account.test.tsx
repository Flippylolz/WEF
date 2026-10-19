import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as auth from "@/lib/auth-api";
import * as favorites from "@/lib/favorites-api";
import * as history from "@/lib/view-history-api";
import { useExplorerAccount } from "./use-explorer-account";

const account: auth.Account = {
  id: "account",
  username: "warsaw",
  role: "user",
  must_change_password: false,
  created_at: "2026-08-01T00:00:00Z",
  last_login_at: null,
};
function renderAccount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, ...renderHook(useExplorerAccount, { wrapper }) };
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.spyOn(auth, "fetchCurrentAccount").mockResolvedValue({
    state: "ready",
    data: account,
  });
  vi.spyOn(favorites, "fetchFavorites").mockResolvedValue({
    state: "ready",
    data: { items: [] },
  });
  vi.spyOn(history, "startAccountVisit").mockResolvedValue({
    state: "ready",
    data: {
      visit_id: "visit",
      current_visit_at: "2026-08-02T00:00:00Z",
      previous_visit_at: "2026-08-01T00:00:00Z",
    },
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("uses account visits and refreshes successful favorite changes", async () => {
  const add = vi
    .spyOn(favorites, "addFavorite")
    .mockResolvedValue({ state: "ready", data: null });
  const remove = vi
    .spyOn(favorites, "removeFavorite")
    .mockResolvedValue({ state: "error" });
  const { result, client } = renderAccount();
  await waitFor(() =>
    expect(result.current.effectiveLastVisitAt).toBe("2026-08-01T00:00:00Z"),
  );
  expect(result.current.signedIn).toBe(true);
  await act(() => result.current.toggleFavorite("location"));
  expect(add).toHaveBeenCalledWith("location");
  act(() => {
    client.setQueryData(["favorites"], [{ location_id: "location" }]);
  });
  await waitFor(() =>
    expect(result.current.favoriteIds.has("location")).toBe(true),
  );
  const invalidate = vi.spyOn(client, "invalidateQueries");
  await act(() => result.current.toggleFavorite("location"));
  expect(remove).toHaveBeenCalledWith("location");
  expect(invalidate).not.toHaveBeenCalled();
});

it("keeps account browsing available when favorites fail", async () => {
  vi.mocked(favorites.fetchFavorites).mockResolvedValue({ state: "error" });
  const { result, client } = renderAccount();
  await waitFor(() =>
    expect(client.getQueryState(["favorites"])?.status).toBe("error"),
  );
  expect(result.current.signedIn).toBe(true);
  expect(result.current.favoriteIds.size).toBe(0);
});

it("falls back to a fresh account visit id when browser storage access is denied", async () => {
  vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
    throw new Error("denied");
  });
  vi.spyOn(window, "sessionStorage", "get").mockImplementation(() => {
    throw new Error("denied");
  });
  const { result } = renderAccount();
  await waitFor(() => expect(history.startAccountVisit).toHaveBeenCalled());
  expect(vi.mocked(history.startAccountVisit).mock.calls[0]?.[0]).toMatch(
    /^[0-9a-f-]{36}$/,
  );
  await waitFor(() =>
    expect(result.current.effectiveLastVisitAt).toBe("2026-08-01T00:00:00Z"),
  );
});

it("does not update browser-visit state after unmount", async () => {
  const { unmount } = renderAccount();
  unmount();
  await act(async () => {
    await Promise.resolve();
  });
  expect(history.startAccountVisit).not.toHaveBeenCalled();
});

it("refuses a forced account-visit request before an account exists", async () => {
  vi.mocked(auth.fetchCurrentAccount).mockResolvedValue({ state: "error" });
  const { result, client } = renderAccount();
  await waitFor(() => expect(result.current.accountQuery.isError).toBe(true));
  const visit = client
    .getQueryCache()
    .find({ queryKey: ["view-history", "visit"], exact: false });
  await act(async () => {
    await expect(visit!.fetch()).rejects.toThrow("missing visit");
  });
  expect(history.startAccountVisit).not.toHaveBeenCalled();
});
