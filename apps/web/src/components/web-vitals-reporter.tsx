"use client";

import { useEffect } from "react";

import { startWebVitalsCollection } from "@/lib/web-vitals";

export function WebVitalsReporter() {
  useEffect(() => {
    startWebVitalsCollection();
  }, []);

  return null;
}
