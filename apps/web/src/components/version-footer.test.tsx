import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  resolveReleaseVersion,
  VersionBadge,
} from "@/components/version-footer";

const RELEASE_SHA = "1ec30c0223806ec62e30ea22fea8b22e99a0aa12";

afterEach(() => {
  cleanup();
});

describe("VersionBadge", () => {
  it("renders a short release SHA in the floating badge", () => {
    render(<VersionBadge releaseSha={RELEASE_SHA} />);

    expect(
      screen.getByLabelText("Application version 1ec30c0"),
    ).toHaveTextContent("version: 1ec30c0");
    expect(screen.getByText("1ec30c0", { selector: "code" })).toBeVisible();
  });

  it("shortens a valid release SHA consistently", () => {
    expect(resolveReleaseVersion(RELEASE_SHA)).toBe(RELEASE_SHA.slice(0, 7));
  });

  it("uses a stable development label without a valid release SHA", () => {
    expect(resolveReleaseVersion(undefined)).toBe("development");
    expect(resolveReleaseVersion("not-a-release-sha")).toBe("development");
  });
});
