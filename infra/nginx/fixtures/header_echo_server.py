"""Header-echo fixture upstream for shared-edge proofs.

Serves one JSON response describing the request so proofs can assert edge
routing decisions and forwarded proxy headers. Proof scaffolding only: it is
never deployed and holds no secrets.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class EchoHandler(BaseHTTPRequestHandler):
    server_version = "wef-edge-fixture/1"
    sys_version = ""

    def _respond(self, body_bytes: bytes = b"") -> None:
        payload = {
            "fixture": os.environ.get("FIXTURE_NAME", "unknown"),
            "method": self.command,
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body_length": len(body_bytes),
        }
        encoded = json.dumps(payload, sort_keys=True).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self._respond()

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        self._respond(self.rfile.read(length) if length else b"")

    def do_PUT(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        self._respond(self.rfile.read(length) if length else b"")

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    address = ("", 8080)
    ThreadingHTTPServer(address, EchoHandler).serve_forever()


if __name__ == "__main__":
    main()
