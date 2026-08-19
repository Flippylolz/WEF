export type WebVitalRating = "good" | "needs-improvement" | "poor";

export type WebVitalMetric = {
  name: string;
  value: number;
  rating: WebVitalRating;
  navigationType?: string;
};

export type WebVitalsSink = (metric: WebVitalMetric) => void;

let sink: WebVitalsSink | null = null;

export function setWebVitalsSink(next: WebVitalsSink | null): void {
  sink = next;
}

export function reportWebVital(metric: WebVitalMetric): void {
  sink?.(metric);
}

export function startWebVitalsCollection(): void {
  if (typeof window === "undefined") return;

  void import("web-vitals").then(({ onCLS, onFCP, onINP, onLCP, onTTFB }) => {
    const relay = (metric: {
      name: string;
      value: number;
      rating: string;
      navigationType?: string;
    }) => {
      reportWebVital({
        name: metric.name,
        value: metric.value,
        rating: metric.rating as WebVitalRating,
        navigationType: metric.navigationType,
      });
    };

    onCLS(relay);
    onFCP(relay);
    onLCP(relay);
    onINP(relay);
    onTTFB(relay);
  });
}
