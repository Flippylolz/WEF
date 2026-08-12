"use client";

import { useTranslations } from "next-intl";

import type { components } from "@/generated/api";

export type EstateResponse = components["schemas"]["EstateResponse"];

type EstateListProps = {
  estates: EstateResponse[];
};

export function EstateList({ estates }: EstateListProps) {
  const t = useTranslations();

  return (
    <ul className="estate-grid">
      {estates.map((estate) => (
        <li className="estate-card" key={estate.id}>
          <article>
            <div className="estate-heading">
              <h2>{estate.title}</h2>
              <span className="availability">
                {t(estate.availability_label_key)}
              </span>
            </div>
            <p className="coordinates">
              {estate.location.latitude}, {estate.location.longitude}
            </p>
          </article>
        </li>
      ))}
    </ul>
  );
}
