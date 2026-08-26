import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WebVitalsReporter } from "@/components/web-vitals-reporter";
import * as webVitals from "@/lib/web-vitals";

describe("WebVitalsReporter", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts collection once on mount", async () => {
    const start = vi
      .spyOn(webVitals, "startWebVitalsCollection")
      .mockImplementation(() => undefined);
    render(<WebVitalsReporter />);
    await waitFor(() => expect(start).toHaveBeenCalledOnce());
  });
});
