"use client";

import type { components } from "@/generated/api";
import { useTranslations } from "next-intl";

type Props = {
  accuracy?: components["schemas"]["LocationAccuracy"] | null;
  confidence?: string;
};

export function LocationAccuracy({ accuracy, confidence }: Props) {
  const t = useTranslations("map");
  const known =
    accuracy &&
    ["building", "street", "area", "unresolved"].includes(accuracy.precision);
  return (
    <span
      className="location-accuracy"
      data-precision={known ? accuracy.precision : "unresolved"}
    >
      <span>{known ? accuracy.label : t("locationUnresolved")}</span>
      {confidence === "low" ||
      accuracy?.uncertainty_reason === "low_location_confidence" ? (
        <span className="confidence-note">
          {t("locationConfidenceLimited")}
        </span>
      ) : null}
    </span>
  );
}
