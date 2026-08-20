"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ComponentProps } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { Account } from "@/lib/auth-api";
import {
  changePassword,
  loginAccount,
  logoutAccount,
  registerAccount,
  revokeAllSessions,
} from "@/lib/auth-api";

const usernameSchema = z
  .string()
  .trim()
  .min(3, "usernameMin")
  .max(64, "usernameMax")
  .regex(/^[A-Za-z0-9_-]+$/, "usernamePattern");

const passwordSchema = z
  .string()
  .min(10, "passwordMin")
  .max(256, "passwordMax");

const loginSchema = z.object({
  username: usernameSchema,
  password: passwordSchema,
});

const registerSchema = loginSchema
  .extend({
    confirmPassword: passwordSchema,
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "passwordMismatch",
    path: ["confirmPassword"],
  });

const changePasswordSchema = z
  .object({
    currentPassword: passwordSchema,
    newPassword: passwordSchema,
    confirmNewPassword: passwordSchema,
  })
  .refine((values) => values.newPassword === values.confirmNewPassword, {
    message: "passwordMismatch",
    path: ["confirmNewPassword"],
  });

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;
type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

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

type AuthenticatedPanelProps = {
  onAuthenticated: (account: Account) => void;
};

function LoginPanel({ onAuthenticated }: AuthenticatedPanelProps) {
  const t = useTranslations("auth");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  return (
    <form
      className="account-form"
      onSubmit={handleSubmit(async (values) => {
        const result = await loginAccount(values);
        if (result.state === "error") {
          setError("root", {
            message: result.message ?? t("loginFailed"),
          });
          return;
        }
        onAuthenticated(result.data);
      })}
    >
      <Field
        id="login-username"
        label={t("usernameLabel")}
        error={fieldError(t, errors.username?.message)}
        inputProps={register("username")}
      />
      <Field
        id="login-password"
        label={t("passwordLabel")}
        type="password"
        error={fieldError(t, errors.password?.message)}
        inputProps={register("password")}
      />
      {errors.root ? (
        <p className="form-error" role="alert">
          {errors.root.message}
        </p>
      ) : null}
      <button className="button-primary" type="submit" disabled={isSubmitting}>
        {t("loginAction")}
      </button>
    </form>
  );
}

function RegisterPanel({ onAuthenticated }: AuthenticatedPanelProps) {
  const t = useTranslations("auth");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", password: "", confirmPassword: "" },
  });

  return (
    <form
      className="account-form"
      onSubmit={handleSubmit(async (values) => {
        const result = await registerAccount({
          username: values.username,
          password: values.password,
        });
        if (result.state === "error") {
          setError("root", {
            message: result.message ?? t("registerFailed"),
          });
          return;
        }
        const login = await loginAccount({
          username: values.username,
          password: values.password,
        });
        if (login.state === "error") {
          setError("root", {
            message: login.message ?? t("loginAfterRegisterFailed"),
          });
          return;
        }
        onAuthenticated(login.data);
      })}
    >
      <Field
        id="register-username"
        label={t("usernameLabel")}
        hint={t("usernameHint")}
        error={fieldError(t, errors.username?.message)}
        inputProps={register("username")}
      />
      <Field
        id="register-password"
        label={t("passwordLabel")}
        type="password"
        hint={t("passwordHint")}
        error={fieldError(t, errors.password?.message)}
        inputProps={register("password")}
      />
      <Field
        id="register-confirm-password"
        label={t("confirmPasswordLabel")}
        type="password"
        error={fieldError(t, errors.confirmPassword?.message)}
        inputProps={register("confirmPassword")}
      />
      {errors.root ? (
        <p className="form-error" role="alert">
          {errors.root.message}
        </p>
      ) : null}
      <button className="button-primary" type="submit" disabled={isSubmitting}>
        {t("registerAction")}
      </button>
    </form>
  );
}

type SignedInPanelProps = {
  account: Account;
  onLoggedOut: () => void;
  onClose: () => void;
  onNotice?: (message: string | null) => void;
};

function SignedInPanel({
  account,
  onLoggedOut,
  onClose,
  onNotice,
}: SignedInPanelProps) {
  const t = useTranslations("auth");
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

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
    </div>
  );
}

type ChangePasswordPanelProps = {
  forced: boolean;
  onLoggedOut: () => void;
  onClose: () => void;
  onNotice?: (message: string | null) => void;
  onCancel?: () => void;
};

function ChangePasswordPanel({
  forced,
  onLoggedOut,
  onClose,
  onNotice,
  onCancel,
}: ChangePasswordPanelProps) {
  const t = useTranslations("auth");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmNewPassword: "",
    },
  });

  return (
    <form
      className="account-form"
      onSubmit={handleSubmit(async (values) => {
        const result = await changePassword({
          current_password: values.currentPassword,
          new_password: values.newPassword,
        });
        if (result.state === "error") {
          setError("root", {
            message: result.message ?? t("changePasswordFailed"),
          });
          return;
        }
        onNotice?.(t("passwordChangedNotice"));
        onLoggedOut();
      })}
    >
      {forced ? (
        <p className="account-modal-notice" role="status">
          {t("forcedPasswordNotice")}
        </p>
      ) : null}
      <Field
        id="current-password"
        label={t("currentPasswordLabel")}
        type="password"
        error={fieldError(t, errors.currentPassword?.message)}
        inputProps={register("currentPassword")}
      />
      <Field
        id="new-password"
        label={t("newPasswordLabel")}
        type="password"
        hint={t("passwordHint")}
        error={fieldError(t, errors.newPassword?.message)}
        inputProps={register("newPassword")}
      />
      <Field
        id="confirm-new-password"
        label={t("confirmNewPasswordLabel")}
        type="password"
        error={fieldError(t, errors.confirmNewPassword?.message)}
        inputProps={register("confirmNewPassword")}
      />
      {errors.root ? (
        <p className="form-error" role="alert">
          {errors.root.message}
        </p>
      ) : null}
      <button className="button-primary" type="submit" disabled={isSubmitting}>
        {t("changePasswordAction")}
      </button>
      {onCancel ? (
        <button className="button-secondary" type="button" onClick={onCancel}>
          {t("backToAccountAction")}
        </button>
      ) : null}
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
    </form>
  );
}

type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  type?: string;
  error?: string;
  inputProps: ComponentProps<"input">;
};

function Field({
  id,
  label,
  hint,
  type = "text",
  error,
  inputProps,
}: FieldProps) {
  return (
    <label className="form-field" htmlFor={id}>
      <span>{label}</span>
      <input id={id} type={type} autoComplete="off" {...inputProps} />
      {hint ? <small>{hint}</small> : null}
      {error ? (
        <span className="form-error" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
}

function fieldError(
  t: ReturnType<typeof useTranslations<"auth">>,
  code: string | undefined,
) {
  if (!code) return undefined;
  if (
    code === "usernameMin" ||
    code === "usernameMax" ||
    code === "usernamePattern" ||
    code === "passwordMin" ||
    code === "passwordMax" ||
    code === "passwordMismatch"
  ) {
    return t(code);
  }
  return code;
}
