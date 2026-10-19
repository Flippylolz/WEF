"use client";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";
import type { Account } from "@/lib/auth-api";
import {
  ChangePasswordPanel,
  LoginPanel,
  RegisterPanel,
} from "@/components/account/auth-forms";
import { SignedInPanel } from "@/components/account/signed-in-panel";

export type AccountModalMode = "login" | "register" | "account" | "password";

type AccountModalProps = {
  open: boolean;
  account: Account | null | undefined;
  initialMode: AccountModalMode;
  notice?: string | null;
  onClose: () => void;
  onAuthenticated: (account: Account) => void;
  onLoggedOut: () => void;
  onNotice?: (message: string | null) => void;
};

export function AccountModal({
  open,
  account,
  initialMode,
  notice = null,
  onClose,
  onAuthenticated,
  onLoggedOut,
  onNotice,
}: AccountModalProps) {
  const t = useTranslations("auth");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const forcedChange = Boolean(account?.must_change_password);
  const mode: AccountModalMode = (() => {
    if (!account) {
      return initialMode === "register" ? "register" : "login";
    }
    if (forcedChange || initialMode === "password") {
      return "password";
    }
    return "account";
  })();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const title =
    mode === "password"
      ? forcedChange
        ? t("forcedPasswordTitle")
        : t("changePasswordTitle")
      : mode === "account"
        ? t("signedInTitle")
        : mode === "register"
          ? t("registerTitle")
          : t("loginTitle");

  return (
    <dialog
      ref={dialogRef}
      className="account-modal"
      aria-labelledby="account-modal-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
    >
      <div className="account-modal-panel">
        <header className="account-modal-header">
          <div>
            <p className="eyebrow">{t("eyebrow")}</p>
            <h2 id="account-modal-title">{title}</h2>
          </div>
          <button
            className="account-modal-close"
            type="button"
            aria-label={t("close")}
            onClick={onClose}
          >
            ×
          </button>
        </header>

        {notice ? (
          <p className="account-modal-notice" role="status">
            {notice}
          </p>
        ) : null}

        {mode === "password" && account ? (
          <ChangePasswordPanel
            forced={forcedChange}
            onLoggedOut={onLoggedOut}
            onClose={onClose}
            onNotice={onNotice}
          />
        ) : mode === "account" && account ? (
          <SignedInPanel
            account={account}
            onLoggedOut={onLoggedOut}
            onClose={onClose}
            onNotice={onNotice}
          />
        ) : mode === "register" ? (
          <RegisterPanel onAuthenticated={onAuthenticated} />
        ) : (
          <LoginPanel onAuthenticated={onAuthenticated} />
        )}
      </div>
    </dialog>
  );
}
