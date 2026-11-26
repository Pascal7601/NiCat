#!/usr/bin/env python3
"""Small, authorized-only GET probe, not a stress test or DoS tool.

Never logs authorization headers, response bodies, cookies or account identifiers.
Designed for NiCat staging; defaults to low concurrency and request count.
"""
import argparse
import concurrent.futures
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    p = argparse.ArgumentParser(description="Authorized, bounded NiCat staging GET probe")
    p.add_argument("--url", required=True, help="Staging GET endpoint (full URL)")
    p.add_argument("--requests", type=int, default=20)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--authorized", action="store_true", help="Confirm target ownership and permission to test")
    args = p.parse_args()
    u = urllib.parse.urlsplit(args.url)
    if not args.authorized:
        p.error("--authorized is required. Only probe systems you own or may test.")
    if u.scheme != "https" and not (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1")):
        p.error("Use HTTPS for staging or HTTP for localhost only.")
    if u.username or u.password or u.fragment or not u.hostname:
        p.error("URL must contain a host and no embedded credentials or fragment.")
    if not 1 <= args.requests <= 100 or not 1 <= args.workers <= 5:
        p.error("Limits: 1-100 requests and 1-5 workers")
    if u.path not in ("/health/", "/api/v1/study-coach/recommendations/"):
        p.error("Only NiCat's health and read-only recommendations endpoints are supported.")
    token = os.environ.get("NICAT_PILOT_BEARER_TOKEN", "").strip()
    if u.path.endswith("/recommendations/") and not token:
        p.error("Set NICAT_PILOT_BEARER_TOKEN in the environment, not command history")

    def one(_):
        headers = {"User-Agent": "NiCat-Beta-Probe/1.0"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(args.url, headers=headers, method="GET")
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp.read(1)  # never print response body
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
            exc.close()
        except Exception:
            code = 0
        return code, (time.perf_counter() - start) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, range(args.requests)))
    durations = sorted(t for _, t in results)
    counts = {code: sum(1 for c, _ in results if c == code) for code, _ in results}
    ix = max(0, int(0.95 * len(durations) + 0.999999) - 1)
    print(f"Requests: {len(results)} | Status counts: {counts}")
    print(f"Latency ms: p50={statistics.median(durations):.1f}, p95={durations[ix]:.1f}, max={max(durations):.1f}")
    if any(code != 200 for code, _ in results):
        raise SystemExit("Probe detected non-200 responses; investigate before beta")


if __name__ == "__main__":
    main()
