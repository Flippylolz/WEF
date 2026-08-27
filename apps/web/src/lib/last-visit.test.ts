import { describe, expect, it, vi } from "vitest";

import { lastVisitStorageKeys, startBrowserVisit } from "@/lib/last-visit";

function storage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => void values.delete(key),
    setItem: (key: string, value: string) => void values.set(key, value),
    values,
  };
}

describe("startBrowserVisit", () => {
  it("records a baseline on the first visit", () => {
    const local = storage();
    const session = storage();
    const now = new Date("2026-08-27T12:00:00.000Z");

    expect(startBrowserVisit({ local, session }, now)).toBeNull();
    expect(local.values.get(lastVisitStorageKeys.last)).toBe(now.toISOString());
    expect(session.values.get(lastVisitStorageKeys.current)).toBe(
      now.toISOString(),
    );
    expect(session.values.has(lastVisitStorageKeys.previous)).toBe(false);
  });

  it("returns the prior visit and keeps it stable throughout one session", () => {
    const prior = "2026-08-26T08:30:00.000Z";
    const local = storage({ [lastVisitStorageKeys.last]: prior });
    const session = storage();
    const now = new Date("2026-08-27T12:00:00.000Z");

    expect(startBrowserVisit({ local, session }, now)).toBe(prior);
    expect(local.values.get(lastVisitStorageKeys.last)).toBe(now.toISOString());
    expect(
      startBrowserVisit(
        { local, session },
        new Date("2026-08-27T14:00:00.000Z"),
      ),
    ).toBe(prior);
    expect(local.values.get(lastVisitStorageKeys.last)).toBe(now.toISOString());
  });

  it("ignores corrupt timestamps and unavailable storage", () => {
    const local = storage({ [lastVisitStorageKeys.last]: "not-a-timestamp" });
    expect(
      startBrowserVisit(
        { local, session: storage() },
        new Date("2026-08-27T12:00:00.000Z"),
      ),
    ).toBeNull();

    const unavailable = {
      getItem: vi.fn(() => {
        throw new Error("blocked");
      }),
      removeItem: vi.fn(),
      setItem: vi.fn(),
    };
    expect(
      startBrowserVisit({ local: unavailable, session: storage() }),
    ).toBeNull();
  });
});
