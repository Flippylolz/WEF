import { afterEach, describe, expect, it, vi } from "vitest";

import {
  reportWebVital,
  setWebVitalsSink,
  startWebVitalsCollection,
  type WebVitalMetric,
} from "@/lib/web-vitals";

const webVitals = vi.hoisted(() => ({
  onCLS: vi.fn(),
  onFCP: vi.fn(),
  onINP: vi.fn(),
  onLCP: vi.fn(),
  onTTFB: vi.fn(),
}));

vi.mock("web-vitals", () => ({
  onCLS: (callback: (metric: object) => void) => webVitals.onCLS(callback),
  onFCP: (callback: (metric: object) => void) => webVitals.onFCP(callback),
  onINP: (callback: (metric: object) => void) => webVitals.onINP(callback),
  onLCP: (callback: (metric: object) => void) => webVitals.onLCP(callback),
  onTTFB: (callback: (metric: object) => void) => webVitals.onTTFB(callback),
}));

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

  it("relays collected web-vitals metrics to the sink", async () => {
    const received: WebVitalMetric[] = [];
    setWebVitalsSink((metric) => {
      received.push(metric);
    });
    for (const name of ["onCLS", "onFCP", "onINP", "onLCP", "onTTFB"] as const) {
      webVitals[name].mockImplementation((callback: (metric: object) => void) =>
        callback({
          name: name.slice(2),
          value: 1,
          rating: "good",
          navigationType: "navigate",
        }),
      );
    }

    startWebVitalsCollection();

    await vi.waitFor(() => expect(received).toHaveLength(5));
    expect(received.map((metric) => metric.name).sort()).toEqual([
      "CLS",
      "FCP",
      "INP",
      "LCP",
      "TTFB",
    ]);
  });
});
