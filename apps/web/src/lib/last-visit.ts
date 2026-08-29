const LAST_VISIT_KEY = "wef:last-visit-started-at";
const CURRENT_VISIT_KEY = "wef:current-visit-started-at";
const PREVIOUS_VISIT_KEY = "wef:previous-visit-started-at";
const ACCOUNT_VISIT_KEY_PREFIX = "wef:account-visit-id:";

type VisitStorage = Pick<Storage, "getItem" | "removeItem" | "setItem">;

type VisitStoragePair = {
  local: VisitStorage;
  session: VisitStorage;
};

function validTimestamp(value: string | null) {
  if (value === null) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString() !== value) {
    return null;
  }
  return value;
}

export function startBrowserVisit(
  storage: VisitStoragePair,
  now = new Date(),
): string | null {
  try {
    const currentVisit = validTimestamp(
      storage.session.getItem(CURRENT_VISIT_KEY),
    );
    if (currentVisit !== null) {
      return validTimestamp(storage.session.getItem(PREVIOUS_VISIT_KEY));
    }

    const previousVisit = validTimestamp(storage.local.getItem(LAST_VISIT_KEY));
    const currentVisitStartedAt = now.toISOString();
    storage.session.setItem(CURRENT_VISIT_KEY, currentVisitStartedAt);
    if (previousVisit === null) {
      storage.session.removeItem(PREVIOUS_VISIT_KEY);
    } else {
      storage.session.setItem(PREVIOUS_VISIT_KEY, previousVisit);
    }
    storage.local.setItem(LAST_VISIT_KEY, currentVisitStartedAt);
    return previousVisit;
  } catch {
    // Browsing can continue when privacy settings make Web Storage unavailable.
    return null;
  }
}

export function getOrCreateAccountVisitId(
  storage: VisitStorage,
  accountId: string,
  createId: () => string = () => crypto.randomUUID(),
): string {
  const key = `${ACCOUNT_VISIT_KEY_PREFIX}${accountId}`;
  try {
    const existing = storage.getItem(key);
    if (existing !== null) return existing;
    const visitId = createId();
    storage.setItem(key, visitId);
    return visitId;
  } catch {
    // The server still receives a visit when browser storage is unavailable.
    return createId();
  }
}

export const lastVisitStorageKeys = {
  current: CURRENT_VISIT_KEY,
  last: LAST_VISIT_KEY,
  previous: PREVIOUS_VISIT_KEY,
  accountPrefix: ACCOUNT_VISIT_KEY_PREFIX,
} as const;
