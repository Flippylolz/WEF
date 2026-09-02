import { NextRequest, NextResponse } from "next/server";

// Per-request nonce CSP layered over the shared edge policy (which stays
// generic): browsers enforce every CSP header, so script execution requires
// this app-issued nonce even though the edge keeps 'unsafe-inline'. Matches
// the edge directive set in infra/nginx/tls.conf.in otherwise.
function contentSecurityPolicy(nonce: string, isDev: boolean): string {
  return [
    "default-src 'self'",
    isDev
      ? "connect-src 'self' ws://localhost:* http://localhost:* https://tiles.openfreemap.org https://*.openfreemap.org"
      : "connect-src 'self' https://tiles.openfreemap.org https://*.openfreemap.org",
    "font-src 'self' data:",
    "img-src 'self' data: blob: https://tiles.openfreemap.org https://*.openfreemap.org https://tile.openstreetmap.org",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    isDev
      ? `script-src 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
      : `script-src 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "worker-src 'self' blob:",
  ].join("; ");
}

export function middleware(request: NextRequest) {
  const isDev = process.env.NODE_ENV !== "production";
  const nonce = btoa(crypto.randomUUID());

  const requestHeaders = new Headers(request.headers);
  const csp = contentSecurityPolicy(nonce, isDev);
  // Next.js reads the request-side CSP to stamp its own scripts with the
  // nonce; the response header enforces the policy in the browser.
  requestHeaders.set("Content-Security-Policy", csp);
  requestHeaders.set("x-nonce", nonce);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [
    "/((?!api|media|vendor|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
