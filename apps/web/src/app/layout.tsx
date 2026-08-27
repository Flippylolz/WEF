import type { Metadata, Viewport } from "next";
import { connection } from "next/server";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { VersionBadge } from "@/components/version-footer";
import { WebVitalsReporter } from "@/components/web-vitals-reporter";

import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";

export const metadata: Metadata = {
  title: {
    default: "Warsaw Estate Finder",
    template: "%s | Warsaw Estate Finder",
  },
  description:
    "Browse apartments and houses offered for sale across Warsaw on an interactive map.",
  applicationName: "Warsaw Estate Finder",
  metadataBase: new URL("https://wef.invalid"),
  openGraph: {
    title: "Warsaw Estate Finder",
    description:
      "Browse apartments and houses offered for sale across Warsaw on an interactive map.",
    type: "website",
    locale: "en_GB",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0d1117",
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
          <NextIntlClientProvider>
            {children}
            <WebVitalsReporter />
          </NextIntlClientProvider>
        </div>
        <VersionBadge />
      </body>
    </html>
  );
}
