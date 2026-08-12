import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import messages from "../../messages/en.json";
import { EstateList, type EstateResponse } from "./estate-list";

const estates: EstateResponse[] = [
  {
    id: 1,
    title: "North House",
    location: { latitude: 52.52, longitude: 13.405 },
    availability: "available",
    availability_label_key: "estates.availability.available",
  },
  {
    id: 2,
    title: "South House",
    location: { latitude: 48.137, longitude: 11.576 },
    availability: "reserved",
    availability_label_key: "estates.availability.reserved",
  },
];

describe("EstateList", () => {
  it("renders backend DTOs and translates backend-provided label keys", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <EstateList estates={estates} />
      </NextIntlClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "North House" }),
    ).toBeInTheDocument();
    expect(screen.getByText("52.52, 13.405")).toBeInTheDocument();
    expect(screen.getByText("Available")).toBeInTheDocument();
    expect(screen.getByText("Reserved")).toBeInTheDocument();
  });
});
