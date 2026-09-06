"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { fetchCurrentAccount } from "@/lib/auth-api";
import {
  addFavorite,
  fetchFavorites,
  removeFavorite,
} from "@/lib/favorites-api";
import { getOrCreateAccountVisitId, startBrowserVisit } from "@/lib/last-visit";
import { startAccountVisit } from "@/lib/view-history-api";

export function useExplorerAccount() {
  const queryClient = useQueryClient();
  const [lastVisitAt, setLastVisitAt] = useState<string | null | undefined>(
    undefined,
  );
  useEffect(() => {
    let previousVisit: string | null = null;
    try {
      previousVisit = startBrowserVisit({
        local: window.localStorage,
        session: window.sessionStorage,
      });
    } catch {
      // Accessing a storage area itself can be blocked by browser privacy mode.
    }
    let mounted = true;
    queueMicrotask(() => {
      if (mounted) setLastVisitAt(previousVisit);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const accountQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async ({ signal }) => {
      const result = await fetchCurrentAccount({ signal });
      if (result.state === "error") throw new Error("auth");
      return result.data;
    },
  });
  const signedIn = accountQuery.isSuccess && accountQuery.data !== null;
  const accountVisitId = useMemo(() => {
    const accountId = accountQuery.data?.id;
    if (accountId === undefined || typeof window === "undefined") return null;
    try {
      return getOrCreateAccountVisitId(
        window.sessionStorage,
        String(accountId),
      );
    } catch {
      // Accessing the storage area itself can be blocked in privacy mode.
      return crypto.randomUUID();
    }
  }, [accountQuery.data?.id]);
  const accountVisitQuery = useQuery({
    queryKey: ["view-history", "visit", accountQuery.data?.id, accountVisitId],
    enabled: signedIn && accountVisitId !== null,
    queryFn: async ({ signal }) => {
      if (accountVisitId === null) throw new Error("missing visit");
      const result = await startAccountVisit(accountVisitId, { signal });
      if (result.state === "error") throw new Error("view-history");
      return result.data;
    },
    staleTime: Number.POSITIVE_INFINITY,
  });
  const effectiveLastVisitAt =
    signedIn && accountVisitQuery.isPending
      ? null
      : signedIn && accountVisitQuery.isSuccess
        ? accountVisitQuery.data.previous_visit_at
        : lastVisitAt;
  const favoritesQuery = useQuery({
    queryKey: ["favorites"],
    enabled: signedIn,
    queryFn: async ({ signal }) => {
      const result = await fetchFavorites({ signal });
      if (result.state === "error") throw new Error("favorites");
      return result.data.items;
    },
  });
  const favoriteIds = useMemo(
    () =>
      new Set(
        (favoritesQuery.data ?? []).map((item) => String(item.location_id)),
      ),
    [favoritesQuery.data],
  );
  async function toggleFavorite(locationId: string) {
    const starred = favoriteIds.has(locationId);
    const result = starred
      ? await removeFavorite(locationId)
      : await addFavorite(locationId);
    if (result.state === "ready") {
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
    }
  }
  return {
    accountQuery,
    signedIn,
    effectiveLastVisitAt,
    favoriteIds,
    toggleFavorite,
  };
}
