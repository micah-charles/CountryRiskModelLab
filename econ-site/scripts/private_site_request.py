#!/usr/bin/env python3
"""Authenticated Site API request; receive ephemeral credentials on hidden stdin.

No token is accepted on the command line or written to disk. Redirects are
rejected so the platform access token cannot be forwarded to another origin.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import sys
import termios
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    original = None
    if sys.stdin.isatty():
        original = termios.tcgetattr(sys.stdin.fileno())
        hidden = original[:]
        hidden[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, hidden)
    print("Ready for private Site request JSON on stdin (input hidden).", flush=True)
    try:
        config = json.loads(sys.stdin.readline())
    finally:
        if original is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, original)
    url = urllib.parse.urlsplit(config["url"])
    if url.scheme != "https" or not url.hostname or not url.hostname.endswith(".chatgpt.site") or url.username or url.password or not url.path.startswith("/api/"):
        raise SystemExit("Only HTTPS ChatGPT Site API endpoints are supported")
    if urllib.parse.urlunsplit((url.scheme, url.netloc, "", "", "")) != config["site_origin"]:
        raise SystemExit("Request origin does not match the selected Site")
    token = config.get("token")
    if not isinstance(token, str) or not token:
        raise SystemExit("Ephemeral platform access credential is missing")
    method = config.get("method", "GET")
    if method not in {"GET", "POST"}:
        raise SystemExit("Unsupported request method")
    body = None
    if config.get("payload_file"):
        body = Path(config["payload_file"]).read_bytes()
    elif method == "POST":
        body = json.dumps(config.get("body", {})).encode()
    request = urllib.request.Request(config["url"], data=body, method=method, headers={"OAI-Sites-Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(request, timeout=180)
    except urllib.error.HTTPError as exc:
        response = exc
    content_type = response.headers.get("Content-Type", "")
    raw = response.read(25 * 1024 * 1024 + 1)
    if len(raw) > 25 * 1024 * 1024:
        raise SystemExit("Response exceeds the local readback limit")
    status = response.status
    if "image/svg+xml" in content_type and config.get("expect_svg"):
        if status != 200 or b"<svg" not in raw[:500]:
            raise SystemExit("Chart response is not a successful SVG image")
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != response.headers.get("X-Chart-Asset-SHA256"):
            raise SystemExit("Chart response checksum mismatch")
        print(json.dumps({"status": status, "svgVerified": True, "bytes": len(raw), "sha256": actual_hash, "version": response.headers.get("X-Bond-Snapshot-Version")}))
        return
    if "json" not in content_type:
        print(json.dumps({"status": status, "error": "Non-JSON response; sign-in or deployment may be required"}))
        raise SystemExit(1)
    data = json.loads(raw)
    if config.get("response_file"):
        destination = Path(config["response_file"]).resolve()
        private_root = (Path(__file__).resolve().parents[1] / "private-data").resolve()
        if private_root not in destination.parents:
            raise SystemExit("Readback files must remain in the ignored private-data directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
    summary = {"status": status}
    if isinstance(data, dict):
        for key in ["datasetKey", "version", "previousVersion", "restoredFromVersion", "changeCount", "recentChangeCount", "snapshotSha256", "failures", "error", "details"]:
            if key in data:
                summary[key] = data[key]
        summary["keys"] = list(data)
        if isinstance(data.get("snapshot"), dict):
            snapshot = data["snapshot"]
            summary["seriesCounts"] = {key: len(value) for key, value in snapshot.get("series", {}).items()}
    elif isinstance(data, list):
        summary["records"] = len(data)
    print(json.dumps(summary))
    if not 200 <= status < 300:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
