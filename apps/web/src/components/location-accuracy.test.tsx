import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LocationAccuracy } from "./location-accuracy";

vi.mock("next-intl", () => ({ useTranslations: () => (key: string) => key }));
afterEach(cleanup);

it.each([
  ["building", "Building location"],
  ["street", "Approximate street location"],
  ["area", "Approximate area"],
  ["unresolved", "Location unresolved"],
] as const)(
  "renders backend %s precision without interpreting confidence as accuracy",
  (precision, label) => {
    render(
      <LocationAccuracy
        accuracy={{
          precision,
          label,
          validation_status: "accepted",
          uncertainty_reason: null,
        }}
        confidence="high"
      />,
    );
    expect(screen.getByText(label)).toBeVisible();
    expect(
      screen.queryByText("locationConfidenceLimited"),
    ).not.toBeInTheDocument();
  },
);

it("uses explicit uncertainty for missing legacy fields", () => {
  render(<LocationAccuracy confidence="low" />);
  expect(screen.getByText("locationUnresolved")).toBeVisible();
  expect(screen.getByText("locationConfidenceLimited")).toBeVisible();
});

it("shows the backend uncertainty warning independently from offer completeness", () => {
  render(
    <LocationAccuracy
      accuracy={{
        precision: "building",
        label: "Building location",
        validation_status: "accepted",
        uncertainty_reason: "low_location_confidence",
      }}
      confidence="medium"
    />,
  );
  expect(screen.getByText("locationConfidenceLimited")).toBeVisible();
});
