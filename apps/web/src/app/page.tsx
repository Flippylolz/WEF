import { getTranslations } from "next-intl/server";

import { MapExplorer } from "@/components/map-explorer";

export default async function Home() {
  const t = await getTranslations("home");

  return (
    <main className="page-shell" aria-labelledby="page-title">
      <header className="page-header">
        <p className="eyebrow">WEF</p>
        <h1 id="page-title">{t("title")}</h1>
        <p className="subtitle">{t("subtitle")}</p>
      </header>
      <MapExplorer />
    </main>
  );
}
