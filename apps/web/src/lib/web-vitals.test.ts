import { afterEach, describe, expect, it, vi } from "vitest";

import {
  reportWebVital,
  setWebVitalsSink,
  type WebVitalMetric,
} from "@/lib/web-vitals";

describe("web-vitals", () => {
  afterEach(() => {
    setWebVitalsSink(null);
  });

  it("forwards only allowlisted metric fields to an explicit sink", () => {
    const received: WebVitalMetric[] = [];
    setWebVitalsSink((metric) => {
      received.push(metric);
    });

    reportWebVital({
      name: "LCP",
      value: 1800,
      rating: "good",
      navigationType: "navigate",
    });

    expect(received).toEqual([
      {
        name: "LCP",
        value: 1800,
        rating: "good",
        navigationType: "navigate",
      },
    ]);
  });

  it("does not emit when no sink is configured", () => {
    const sink = vi.fn();
    setWebVitalsSink(null);
    reportWebVital({
      name: "CLS",
      value: 0.01,
      rating: "good",
    });
    expect(sink).not.toHaveBeenCalled();
  });

  it("never includes listing, contact, or query data in the metric contract", () => {
    const metric: WebVitalMetric = {
      name: "FCP",
      value: 1200,
      rating: "good",
      navigationType: "reload",
    };
    expect(Object.keys(metric).sort()).toEqual([
      "name",
      "navigationType",
      "rating",
      "value",
    ]);
    expect(JSON.stringify(metric)).not.toMatch(/offer|contact|bbox|telegram/i);
  });
});
