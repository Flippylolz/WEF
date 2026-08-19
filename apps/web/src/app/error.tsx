"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="page-shell error-page" aria-labelledby="error-title">
      <h1 id="error-title">{t("segmentTitle")}</h1>
      <p>{t("segmentBody")}</p>
      <button type="button" onClick={() => reset()}>
        {t("retry")}
      </button>
    </main>
  );
}
