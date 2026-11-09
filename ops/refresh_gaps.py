"""Report how often the refresh workflow really runs, and how it was started.

Prints a markdown summary of the gaps between successful runs since a given time, split by what
started each run (GitHub's own schedule, the outside trigger or a manual start).

Run from the repository root:  .venv/Scripts/python ops/refresh_gaps.py --since 2026-11-10T00:00
"""

import argparse
import json
import statistics
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from faultline.env import load_dotenv, token

REPO = "dhatrineerja/faultline-oss"
BUCKETS = [
    (0.75, "under 45 minutes"),
    (1.5, "45 minutes to 1.5 hours"),
    (3, "1.5 to 3 hours"),
    (6, "3 to 6 hours"),
    (float("inf"), "over 6 hours"),
]


def parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def runs_since(since: datetime) -> list[dict]:
    out, page = [], 1
    query = urllib.parse.quote(f">={since:%Y-%m-%dT%H:%M:%SZ}")
    while True:
        url = (
            f"https://api.github.com/repos/{REPO}/actions/workflows/refresh.yml/runs"
            f"?per_page=100&page={page}&created={query}"
        )
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token('GITHUB_TOKEN')}"}
        )
        batch = json.load(urllib.request.urlopen(req))["workflow_runs"]
        out += batch
        if len(batch) < 100:
            return sorted(out, key=lambda r: r["created_at"])
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True, help="UTC start, for example 2026-11-10T00:00")
    args = parser.parse_args()
    load_dotenv()
    since = datetime.fromisoformat(args.since).replace(tzinfo=UTC)
    now = datetime.now(UTC)
    runs = [r for r in runs_since(since) if r["status"] == "completed"]
    ok = [r for r in runs if r["conclusion"] == "success"]
    times = [parse(r["created_at"]) for r in ok]
    gaps = [(b - a).total_seconds() / 3600 for a, b in pairwise(times)]

    print(f"# Refresh runs since {since:%Y-%m-%d %H:%M} UTC, measured {now:%Y-%m-%d %H:%M} UTC\n")
    by_event = Counter(r["event"] for r in runs)
    print(
        f"Completed runs: {len(runs)} ({len(ok)} successful, {len(runs) - len(ok)} not). "
        f"Started by: {dict(by_event)}\n"
    )
    if len(times) < 2:
        print("Not enough successful runs to measure gaps yet.")
        return
    print(
        f"Gap between successful runs: median {statistics.median(gaps):.2f} h, "
        f"mean {statistics.mean(gaps):.2f} h, longest {max(gaps):.2f} h. "
        f"Time since the last success: {(now - times[-1]).total_seconds() / 3600:.2f} h.\n"
    )
    print("| Gap | Count |\n| --- | --- |")
    for upper, label in BUCKETS:
        lower = next((u for u, _ in reversed(BUCKETS[: BUCKETS.index((upper, label))])), 0)
        print(f"| {label} | {sum(lower <= g < upper for g in gaps)} |")
    span = (times[-1] - times[0]).total_seconds() / 3600
    print(
        f"\nSuccessful runs per hour over {span:.1f} h: {len(ok) / span:.2f} (30-minute target: 2.00)"
    )


if __name__ == "__main__":
    main()
