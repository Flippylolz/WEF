"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  AccountModal,
  type AccountModalMode,
} from "@/components/account-modal";
import { FavoritesPanel } from "@/components/favorites-panel";
import { fetchCurrentAccount, type Account } from "@/lib/auth-api";
import { fetchFavorites, removeFavorite } from "@/lib/favorites-api";

export type AuthIntent = {
  mode: AccountModalMode;
};

export type AuthOpener = (intent: AuthIntent) => void;

type UserToolbarProps = {
  onSelectFavorite?: (locationId: string) => void;
  onRegisterAuthOpener?: (open: AuthOpener) => void;
  onAccountChange?: (account: Account | null) => void;
};

export function UserToolbar({
  onSelectFavorite,
  onRegisterAuthOpener,
  onAccountChange,
}: UserToolbarProps) {
  const t = useTranslations("auth");
  const tf = useTranslations("favorites");
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [favoritesOpen, setFavoritesOpen] = useState(false);
  const [modalMode, setModalMode] = useState<AccountModalMode>("login");
  const [notice, setNotice] = useState<string | null>(null);
  const [dismissedForcedPrompt, setDismissedForcedPrompt] = useState(false);

  const accountQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async ({ signal }) => {
      const result = await fetchCurrentAccount({ signal });
      if (result.state === "error") throw new Error("auth");
      return result.data;
    },
  });

  const account = accountQuery.data;
  const signedIn = accountQuery.isSuccess && account !== null;
  const forcedChange = Boolean(account?.must_change_password);
  const open = modalOpen || (forcedChange && !dismissedForcedPrompt);
  const mode: AccountModalMode = forcedChange
    ? "password"
    : modalMode === "register" && !account
      ? "register"
      : account
        ? modalMode === "password"
          ? "password"
          : "account"
        : modalMode === "register"
          ? "register"
          : "login";

  useEffect(() => {
    onRegisterAuthOpener?.((intent) => {
      setNotice(null);
      setDismissedForcedPrompt(false);
      setModalMode(intent.mode);
      setModalOpen(true);
    });
  }, [onRegisterAuthOpener]);

  const favoritesQuery = useQuery({
    queryKey: ["favorites"],
    enabled: signedIn && !forcedChange,
    queryFn: async ({ signal }) => {
      const result = await fetchFavorites({ signal });
      if (result.state === "error") throw new Error("favorites");
      return result.data.items;
    },
  });

  function openModal(nextMode: AccountModalMode) {
    setNotice(null);
    setDismissedForcedPrompt(false);
    setModalMode(nextMode);
    setModalOpen(true);
  }

  function setAccount(next: Account | null) {
    queryClient.setQueryData(["auth", "me"], next);
    onAccountChange?.(next);
    if (next === null) {
      queryClient.removeQueries({ queryKey: ["favorites"] });
    }
  }

  return (
    <>
      <div className="user-toolbar" aria-label={t("toolbarLabel")}>
        {signedIn ? (
          <>
            {!forcedChange ? (
              <button
                className="button-secondary user-toolbar-button user-toolbar-star"
                type="button"
                aria-label={tf("openList")}
                title={tf("openList")}
                onClick={() => setFavoritesOpen(true)}
              >
                ★
              </button>
            ) : null}
            <button
              className="button-secondary user-toolbar-button"
              type="button"
              aria-haspopup="dialog"
              onClick={() => openModal(forcedChange ? "password" : "account")}
            >
              {account?.username}
            </button>
          </>
        ) : (
          <>
            <button
              className="button-secondary user-toolbar-button"
              type="button"
              onClick={() => openModal("login")}
            >
              {t("loginAction")}
            </button>
            <button
              className="button-primary user-toolbar-button"
              type="button"
              onClick={() => openModal("register")}
            >
              {t("registerAction")}
            </button>
          </>
        )}
      </div>
      <AccountModal
        open={open}
        account={account}
        initialMode={mode}
        notice={notice}
        onClose={() => {
          setModalOpen(false);
          setNotice(null);
          if (forcedChange) {
            setDismissedForcedPrompt(true);
          }
        }}
        onAuthenticated={(next) => {
          setAccount(next);
          setNotice(null);
          setDismissedForcedPrompt(false);
          if (next.must_change_password) {
            setModalMode("password");
            setModalOpen(true);
            return;
          }
          setModalOpen(false);
        }}
        onLoggedOut={() => {
          setAccount(null);
          setDismissedForcedPrompt(false);
          setModalMode("login");
          setModalOpen(true);
        }}
        onNotice={setNotice}
      />
      <FavoritesPanel
        open={favoritesOpen}
        items={favoritesQuery.data ?? []}
        loading={favoritesQuery.isPending}
        onClose={() => setFavoritesOpen(false)}
        onSelect={(locationId) => onSelectFavorite?.(locationId)}
        onRemove={async (locationId) => {
          const result = await removeFavorite(locationId);
          if (result.state !== "ready") return false;
          await queryClient.invalidateQueries({ queryKey: ["favorites"] });
          return true;
        }}
      />
    </>
  );
}
