"use client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import {
  deleteOwnAccount,
  disableOwnAccount,
  logoutAccount,
  revokeAllSessions,
  type Account,
} from "@/lib/auth-api";
import { ChangePasswordPanel } from "./auth-forms";

type SignedInPanelProps = {
  account: Account;
  onLoggedOut: () => void;
  onClose: () => void;
  onNotice?: (message: string | null) => void;
};

export function SignedInPanel({
  account,
  onLoggedOut,
  onClose,
  onNotice,
}: SignedInPanelProps) {
  const t = useTranslations("auth");
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [dangerAction, setDangerAction] = useState<"disable" | "delete" | null>(
    null,
  );

  if (showPasswordForm) {
    return (
      <ChangePasswordPanel
        forced={false}
        onLoggedOut={onLoggedOut}
        onClose={onClose}
        onNotice={onNotice}
        onCancel={() => setShowPasswordForm(false)}
      />
    );
  }

  return (
    <div className="account-form">
      <dl className="account-summary">
        <div>
          <dt>{t("usernameLabel")}</dt>
          <dd>{account.username}</dd>
        </div>
        <div>
          <dt>{t("roleLabel")}</dt>
          <dd>{account.role}</dd>
        </div>
      </dl>
      {actionError ? (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      ) : null}
      <button
        className="button-secondary"
        type="button"
        onClick={() => setShowPasswordForm(true)}
      >
        {t("changePasswordAction")}
      </button>
      <button
        className="button-secondary"
        type="button"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setActionError(null);
          const result = await revokeAllSessions();
          setBusy(false);
          if (result.state === "error") {
            setActionError(result.message ?? t("revokeSessionsFailed"));
            return;
          }
          onNotice?.(t("sessionsRevokedNotice"));
          onLoggedOut();
        }}
      >
        {t("revokeSessionsAction")}
      </button>
      <p className="account-modal-hint">{t("revokeSessionsHint")}</p>
      <button
        className="button-secondary"
        type="button"
        onClick={async () => {
          const result = await logoutAccount();
          if (result.state === "ready") {
            onNotice?.(null);
            onLoggedOut();
            onClose();
          }
        }}
      >
        {t("logoutAction")}
      </button>
      <section aria-label={t("dangerZoneTitle")} className="account-danger">
        <h3>{t("dangerZoneTitle")}</h3>
        <p className="account-modal-hint">
          {dangerAction === "disable"
            ? t("disableConfirmHint")
            : dangerAction === "delete"
              ? t("deleteConfirmHint")
              : t("dangerZoneHint")}
        </p>
        {dangerAction === null ? (
          <>
            <button
              className="button-danger"
              type="button"
              disabled={busy}
              onClick={() => setDangerAction("disable")}
            >
              {t("disableAction")}
            </button>
            <button
              className="button-danger"
              type="button"
              disabled={busy}
              onClick={() => setDangerAction("delete")}
            >
              {t("deleteAction")}
            </button>
          </>
        ) : (
          <>
            <button
              className="button-danger-solid"
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setActionError(null);
                const result =
                  dangerAction === "disable"
                    ? await disableOwnAccount()
                    : await deleteOwnAccount();
                setBusy(false);
                if (result.state === "error") {
                  setActionError(result.message ?? t("dangerFailed"));
                  return;
                }
                onNotice?.(
                  dangerAction === "disable"
                    ? t("disabledNotice")
                    : t("deletedNotice"),
                );
                onLoggedOut();
                onClose();
              }}
            >
              {dangerAction === "disable"
                ? t("disableConfirmAction")
                : t("deleteConfirmAction")}
            </button>
            <button
              className="button-secondary"
              type="button"
              disabled={busy}
              onClick={() => setDangerAction(null)}
            >
              {t("cancelAction")}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
