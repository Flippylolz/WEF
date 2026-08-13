import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  resolveReleaseVersion,
  VersionFooter,
} from "@/components/version-footer";

const RELEASE_SHA = "1ec30c0223806ec62e30ea22fea8b22e99a0aa12";

afterEach(() => {
  cleanup();
});

describe("VersionFooter", () => {
  it("renders the complete release SHA in the page footer", () => {
    render(<VersionFooter version={RELEASE_SHA} />);

    expect(screen.getByRole("contentinfo")).toHaveTextContent(
      `version: ${RELEASE_SHA}`,
    );
    expect(screen.getByText(RELEASE_SHA, { selector: "code" })).toBeVisible();
  });

  it("uses a stable development label without a valid release SHA", () => {
    expect(resolveReleaseVersion(undefined)).toBe("development");
    expect(resolveReleaseVersion("not-a-release-sha")).toBe("development");
  });
});
