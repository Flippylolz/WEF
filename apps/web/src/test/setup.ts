import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";

// jsdom has no canvas backend; real WebGL behavior belongs to E14-T5.
if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = () => null;
}

if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

if (
  typeof HTMLDialogElement !== "undefined" &&
  !HTMLDialogElement.prototype.showModal
) {
  HTMLDialogElement.prototype.showModal = function showModal(
    this: HTMLDialogElement,
  ) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
}

// Unexpected React/runtime diagnostics must not pass silently in a green test run.
// Tests intentionally exercising a diagnostic may replace the spy explicitly.
let restoreDiagnostics: (() => void) | undefined;
beforeEach(() => {
  const warn = vi.spyOn(console, "warn").mockImplementation((...values) => {
    throw new Error(`Unexpected console.warn: ${values.join(" ")}`);
  });
  const error = vi.spyOn(console, "error").mockImplementation((...values) => {
    throw new Error(`Unexpected console.error: ${values.join(" ")}`);
  });
  restoreDiagnostics = () => {
    warn.mockRestore();
    error.mockRestore();
  };
});
afterEach(() => restoreDiagnostics?.());
