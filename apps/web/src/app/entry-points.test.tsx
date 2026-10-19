import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import ErrorPage from "./error";
import RootLayout, { metadata, viewport } from "./layout";
import Home from "./page";
import requestConfig from "@/i18n/request";
import messages from "../../messages/en.json";

const connection = vi.hoisted(() => vi.fn(async () => {}));
vi.mock("next/server", () => ({ connection }));
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  NextIntlClientProvider: ({ children }: { children: ReactNode }) => children,
}));
vi.mock("next-intl/server", () => ({
  getTranslations: async () => (key: string) => key,
  getRequestConfig: (config: unknown) => config,
}));
vi.mock("@/components/map-explorer", () => ({
  MapExplorer: () => <p>Map explorer</p>,
}));
vi.mock("@/components/query-provider", () => ({
  QueryProvider: ({ children }: { children: ReactNode }) => children,
}));
vi.mock("@/components/version-footer", () => ({
  VersionBadge: () => <span>Release version</span>,
}));
vi.mock("@/components/web-vitals-reporter", () => ({
  WebVitalsReporter: () => <span>Vitals enabled</span>,
}));

afterEach(cleanup);

it("shows the segment error, reports it and retries on request", async () => {
  const error = new Error("segment failed");
  const diagnostic = vi.spyOn(console, "error").mockImplementation(() => {});
  const reset = vi.fn();
  render(<ErrorPage error={error} reset={reset} />);
  expect(screen.getByRole("heading", { name: "segmentTitle" })).toBeVisible();
  expect(diagnostic).toHaveBeenCalledWith(error);
  await userEvent.click(screen.getByRole("button", { name: "retry" }));
  expect(reset).toHaveBeenCalledOnce();
});

it("renders the translated home page with its explorer", async () => {
  render(await Home());
  expect(screen.getByRole("heading", { name: "title" })).toBeInTheDocument();
  expect(screen.getByText("Map explorer")).toBeInTheDocument();
});

it("renders a dynamic document with translation context, release and vitals", async () => {
  const html = renderToStaticMarkup(
    await RootLayout({ children: <p>Catalog</p> }),
  );
  expect(connection).toHaveBeenCalledOnce();
  expect(html).toContain('<html lang="en">');
  expect(html).toContain("Catalog");
  expect(html).toContain("Release version");
  expect(html).toContain("Vitals enabled");
  expect(metadata.applicationName).toBe("Warsaw Estate Finder");
  expect(viewport.initialScale).toBe(1);
});

it("supplies the supported locale and translation messages", async () => {
  expect(
    await requestConfig({ requestLocale: Promise.resolve(undefined) }),
  ).toEqual({ locale: "en", messages });
});
