import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import GlobalError from "./global-error";

afterEach(cleanup);

it("renders a complete fallback document, reports the failure and allows retry", async () => {
  const error = new Error("layout failed");
  const diagnostic = vi.spyOn(console, "error").mockImplementation(() => {});
  const reset = vi.fn();
  render(<GlobalError error={error} reset={reset} />, { container: document });
  expect(document.documentElement).toHaveAttribute("lang", "en");
  expect(
    screen.getByRole("heading", { name: "Something went wrong" }),
  ).toBeVisible();
  expect(diagnostic).toHaveBeenCalledExactlyOnceWith(error);
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(reset).toHaveBeenCalledOnce();
});
