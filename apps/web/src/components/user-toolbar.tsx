"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { AccountModal } from "@/components/account-modal";
import { fetchCurrentAccount, type Account } from "@/lib/auth-api";

export function UserToolbar() {
  const t = useTranslations("auth");
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"login" | "register">("login");

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

  function openModal(mode: "login" | "register") {
    setModalMode(mode);
    setModalOpen(true);
  }

  function setAccount(next: Account | null) {
    queryClient.setQueryData(["auth", "me"], next);
  }

  return (
    <>
      <div className="user-toolbar" aria-label={t("toolbarLabel")}>
        {signedIn && account ? (
          <button
            className="button-secondary user-toolbar-button"
            type="button"
            aria-haspopup="dialog"
            onClick={() => openModal("login")}
          >
            {account.username}
          </button>
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
        open={modalOpen}
        account={account}
        initialMode={modalMode}
        onClose={() => setModalOpen(false)}
        onAuthenticated={(next) => {
          setAccount(next);
          setModalOpen(false);
        }}
        onLoggedOut={() => setAccount(null)}
      />
    </>
  );
}
