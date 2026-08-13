const RELEASE_SHA_PATTERN = /^[0-9a-f]{40}$/;
const DEVELOPMENT_VERSION = "development";

type VersionFooterProps = {
  version?: string;
};

export function resolveReleaseVersion(
  releaseSha: string | undefined = process.env.WEF_RELEASE_SHA,
): string {
  return releaseSha && RELEASE_SHA_PATTERN.test(releaseSha)
    ? releaseSha
    : DEVELOPMENT_VERSION;
}

export function VersionFooter({
  version = resolveReleaseVersion(),
}: VersionFooterProps = {}) {
  return (
    <footer className="version-footer">
      <p>
        version: <code>{version}</code>
      </p>
    </footer>
  );
}
