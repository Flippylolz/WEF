import { expect, test } from "vitest";

test("unexpected runtime warnings and errors fail", () => {
  expect(() => console.warn("synthetic warning probe")).toThrow(
    "Unexpected console.warn",
  );
  expect(() => console.error("synthetic error probe")).toThrow(
    "Unexpected console.error",
  );
});
