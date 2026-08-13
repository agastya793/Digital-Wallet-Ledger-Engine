#!/usr/bin/env python3
"""
Docker HEALTHCHECK script.

Uses only Python stdlib — no pip dependencies required.
This is critical because it runs inside the Docker container where we
don't want to install extra packages just for health checks.

Exit codes:
    0 = healthy (HTTP 200 from /health)
    1 = unhealthy (any error)

Used by:
    HEALTHCHECK in Dockerfile
    docker compose health conditions
"""

import sys
import urllib.request
import urllib.error


def check_health() -> bool:
    """Hit the /health endpoint and verify we get a 200 response."""
    url = "http://localhost:8000/health"
    timeout = 5  # seconds

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


if __name__ == "__main__":
    healthy = check_health()
    sys.exit(0 if healthy else 1)
