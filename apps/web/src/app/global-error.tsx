"use client";

import { useEffect } from "react";

import "./globals.css";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main
          className="page-shell error-page"
          aria-labelledby="global-error-title"
        >
          <h1 id="global-error-title">Something went wrong</h1>
          <p>
            The application hit an unexpected error. Your filters and URL may
            still be preserved in the address bar.
          </p>
          <button type="button" onClick={() => reset()}>
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
