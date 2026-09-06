"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  changePassword,
  loginAccount,
  logoutAccount,
  registerAccount,
  type Account,
} from "@/lib/auth-api";
import { Field, fieldError } from "./field";

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

type AuthenticatedPanelProps = {
  onAuthenticated: (account: Account) => void;
};

export function LoginPanel({ onAuthenticated }: AuthenticatedPanelProps) {
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

export function RegisterPanel({ onAuthenticated }: AuthenticatedPanelProps) {
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

type ChangePasswordPanelProps = {
  forced: boolean;
  onLoggedOut: () => void;
  onClose: () => void;
  onNotice?: (message: string | null) => void;
  onCancel?: () => void;
};

export function ChangePasswordPanel({
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
