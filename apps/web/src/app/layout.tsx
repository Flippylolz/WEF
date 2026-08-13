import type { Metadata } from "next";
import { connection } from "next/server";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { VersionBadge } from "@/components/version-footer";

import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";

export const metadata: Metadata = {
  title: "Warsaw Estate Finder",
  description: "Browse apartments and houses offered for sale across Warsaw.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default async function RootLayout({ children }: RootLayoutProps) {
  await connection();

  return (
    <html lang="en">
      <body>
        <div className="app-content">
          <NextIntlClientProvider>{children}</NextIntlClientProvider>
        </div>
        <VersionBadge />
      </body>
    </html>
  );
}
