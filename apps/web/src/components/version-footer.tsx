const RELEASE_SHA_PATTERN = /^[0-9a-f]{40}$/;
const SHORT_SHA_LENGTH = 7;
const DEVELOPMENT_VERSION = "development";

type VersionBadgeProps = {
  releaseSha?: string;
};

export function resolveReleaseVersion(
  releaseSha: string | undefined = process.env.WEF_RELEASE_SHA,
): string {
  return releaseSha && RELEASE_SHA_PATTERN.test(releaseSha)
    ? releaseSha.slice(0, SHORT_SHA_LENGTH)
    : DEVELOPMENT_VERSION;
}

export function VersionBadge({
  releaseSha = process.env.WEF_RELEASE_SHA,
}: VersionBadgeProps = {}) {
  const version = resolveReleaseVersion(releaseSha);
  return (
    <div
      className="version-badge"
      aria-label={`Application version ${version}`}
    >
      version: <code>{version}</code>
    </div>
  );
}
