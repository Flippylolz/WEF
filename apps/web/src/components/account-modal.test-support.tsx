import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

export const loginAccount = vi.fn();
export const registerAccount = vi.fn();
export const changePassword = vi.fn();
export const revokeAllSessions = vi.fn();
export const logoutAccount = vi.fn();
export const disableOwnAccount = vi.fn();
export const deleteOwnAccount = vi.fn();

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

export const account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user" as const,
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

export function setupAccountModal() {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
}
