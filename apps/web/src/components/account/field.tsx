import type { ComponentProps } from "react";
import type { useTranslations } from "next-intl";

type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  type?: string;
  error?: string;
  inputProps: ComponentProps<"input">;
};

export function Field({
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

export function fieldError(
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
