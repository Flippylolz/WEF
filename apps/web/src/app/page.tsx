import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { MapExplorer } from "@/components/map-explorer";
import { QueryProvider } from "@/components/query-provider";
import { UserToolbar } from "@/components/user-toolbar";

export default async function Home() {
  const t = await getTranslations("home");

  return (
    <main className="page-shell" aria-labelledby="page-title">
      <header className="page-header">
        <p className="eyebrow">WEF</p>
        <h1 id="page-title">{t("title")}</h1>
        <p className="subtitle">{t("subtitle")}</p>
      </header>
      <QueryProvider>
        <UserToolbar />
        <Suspense
          fallback={
            <p className="state-message" role="status">
              Loading Warsaw locations…
            </p>
          }
        >
          <MapExplorer />
        </Suspense>
      </QueryProvider>
    </main>
  );
}
