import { expect, it, vi } from "vitest";
import type { useTranslations } from "next-intl";
import { fieldError } from "./field";

it("preserves server field errors and translates recognized validation codes", () => {
  const translate = vi.fn(
    (code: string) => `translated:${code}`,
  ) as unknown as ReturnType<typeof useTranslations<"auth">>;
  expect(fieldError(translate, undefined)).toBeUndefined();
  expect(fieldError(translate, "server validation failed")).toBe(
    "server validation failed",
  );
  expect(fieldError(translate, "passwordMismatch")).toBe(
    "translated:passwordMismatch",
  );
});
