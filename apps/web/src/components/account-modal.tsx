"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useEffect, useRef, type ComponentProps } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { Account } from "@/lib/auth-api";
import {
  loginAccount,
  logoutAccount,
  registerAccount,
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

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;

type AccountModalProps = {
  open: boolean;
  account: Account | null | undefined;
  initialMode: "login" | "register";
  onClose: () => void;
  onAuthenticated: (account: Account) => void;
  onLoggedOut: () => void;
};

export function AccountModal({
  open,
  account,
  initialMode,
  onClose,
  onAuthenticated,
  onLoggedOut,
}: AccountModalProps) {
  const t = useTranslations("auth");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const mode = account ? "signed-in" : initialMode;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

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
            <h2 id="account-modal-title">
              {mode === "signed-in"
                ? t("signedInTitle")
                : mode === "register"
                  ? t("registerTitle")
                  : t("loginTitle")}
            </h2>
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

        {mode === "signed-in" && account ? (
          <SignedInPanel
            account={account}
            onLoggedOut={onLoggedOut}
            onClose={onClose}
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
};

function SignedInPanel({ account, onLoggedOut, onClose }: SignedInPanelProps) {
  const t = useTranslations("auth");

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
      <button
        className="button-secondary"
        type="button"
        onClick={async () => {
          const result = await logoutAccount();
          if (result.state === "ready") {
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

type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  type?: string;
  error?: string;
  inputProps: ComponentProps<"input">;
};

function Field({ id, label, hint, type = "text", error, inputProps }: FieldProps) {
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
