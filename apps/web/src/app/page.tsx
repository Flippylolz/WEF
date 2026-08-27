import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { MapExplorer } from "@/components/map-explorer";
import { QueryProvider } from "@/components/query-provider";

export default async function Home() {
  const t = await getTranslations("home");

  return (
    <main className="page-shell app-shell" aria-labelledby="page-title">
      <h1 className="sr-only" id="page-title">
        {t("title")}
      </h1>
      <QueryProvider>
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
