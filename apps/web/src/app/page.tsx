import { getTranslations } from "next-intl/server";

import { EstateList } from "@/components/estate-list";
import { fetchEstates } from "@/lib/estates-api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const t = await getTranslations("home");
  const result = await fetchEstates();

  return (
    <main className="page-shell" aria-labelledby="page-title">
      <header className="page-header">
        <p className="eyebrow">WEF</p>
        <h1 id="page-title">{t("title")}</h1>
        <p className="subtitle">{t("subtitle")}</p>
      </header>

      {result.state === "error" ? (
        <p className="state-message state-error" role="alert">
          {t("error")}
        </p>
      ) : result.items.length === 0 ? (
        <p className="state-message" role="status">
          {t("empty")}
        </p>
      ) : (
        <EstateList estates={result.items} />
      )}
    </main>
  );
}
