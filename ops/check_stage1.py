"""Measure the Stage 1 checkpoint: has the 30-minute refresh run reliably for 7 days?

Reads three things and prints a markdown report:
  1. GitHub Actions run history for the refresh workflow (public API); runs started by the GitHub
     schedule or by the outside trigger count, and so do manual starts.
  2. The per-run records the job saves in the lake under metrics/events_api/.
  3. The stored events, to prove nothing was duplicated.

Run from the repository root:  .venv\\Scripts\\python ops\\check_stage1.py
"""

import json
import sys
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from faultline.config import tracked_repos
from faultline.env import load_dotenv, token

REPO = "dhatrineerja/faultline-oss"
# First successful scheduled run after the token-whitespace fix (commit fb4b167).
START = datetime(2026, 11, 1, 19, 50, tzinfo=UTC)
MAX_QUIET_HOURS = 6  # longest allowed stretch without a successful run
DAYS_REQUIRED = 7


def github(path: str):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        headers={"Authorization": f"Bearer {token('GITHUB_TOKEN')}"},
    )
    return json.load(urllib.request.urlopen(req))


def parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def actions_runs() -> list[dict]:
    runs, page = [], 1
    while True:
        batch = github(f"actions/workflows/refresh.yml/runs?per_page=100&page={page}")[
            "workflow_runs"
        ]
        runs += [
            r
            for r in batch
            if parse(r["created_at"]) >= START and r["event"] in ("schedule", "workflow_dispatch")
        ]
        if len(batch) < 100 or parse(batch[-1]["created_at"]) < START:
            return runs
        page += 1


def main() -> int:
    load_dotenv()
    now = datetime.now(UTC)
    runs = [r for r in actions_runs() if r["status"] == "completed"]
    ok = sorted(parse(r["created_at"]) for r in runs if r["conclusion"] == "success")
    failed = [r for r in runs if r["conclusion"] != "success"]
    elapsed = now - START
    expected = int(elapsed.total_seconds() // 1800)
    gaps = [b - a for a, b in zip([*ok, now][:-1], ok[1:] + [now], strict=False)] if ok else []
    longest = max(gaps, default=timedelta(0))

    # A cache inside the git-ignored data/ folder, so reruns only fetch what changed.
    local = Path(__file__).resolve().parents[1] / "data" / "checkpoint_cache"
    local.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=token("HF_DATASET_REPO"),
        repo_type="dataset",
        local_dir=local,
        token=token("HF_TOKEN"),
        allow_patterns=["events_api/**", "metrics/events_api/**", "state/events_api.json"],
    )
    records = [
        json.loads(p.read_text("utf-8")) for p in sorted(local.glob("metrics/events_api/**/*.json"))
    ]
    records = [r for r in records if parse(r["finished_at"]) >= START]
    events = (
        f"read_parquet('{(local / 'events_api').as_posix()}/**/*.parquet', hive_partitioning=false)"
    )
    total, distinct = duckdb.sql(f"select count(*), count(distinct id) from {events}").fetchall()[0]
    per_day = duckdb.sql(
        f"select cast(created_at as date) d, count(*) from {events} "
        f"where created_at >= '{(now - timedelta(days=7)).date()}' group by 1 order by 1"
    ).fetchall()
    state = json.loads((local / "state" / "events_api.json").read_text("utf-8"))
    loadable = len(tracked_repos()) - 5  # five are recorded in config/unmapped.csv

    headroom = [r["rate_remaining_min"] for r in records if r.get("rate_remaining_min") is not None]
    gap_repos = {x for r in records for x in r.get("gap_repos", [])}
    checks = {
        f"{DAYS_REQUIRED} days elapsed since the first good run": elapsed
        >= timedelta(days=DAYS_REQUIRED),
        "no failed scheduled runs": not failed,
        f"no stretch over {MAX_QUIET_HOURS} h without a successful run": longest
        <= timedelta(hours=MAX_QUIET_HOURS),
        "no duplicate event ids in the lake": total == distinct,
        f"state covers all {loadable} loadable repos": len(state) >= loadable,
    }

    print(f"# Stage 1 checkpoint report, measured {now:%Y-%m-%d %H:%M} UTC\n")
    print(
        f"Window: {START:%Y-%m-%d %H:%M} UTC to now ({elapsed.days} days {elapsed.seconds // 3600} h).\n"
    )
    print("| Measure | Value |\n| --- | --- |")
    print(
        f"| Runs completed, scheduled or triggered | {len(runs)} (expected about {expected} at every 30 minutes) |"
    )
    print(f"| Successful / failed | {len(ok)} / {len(failed)} |")
    print(f"| Longest stretch without a successful run | {longest.total_seconds() / 3600:.1f} h |")
    print(f"| Run records saved | {len(records)} |")
    print(
        f"| Runs that stopped early on the rate limit | {sum(bool(r.get('stopped_early')) for r in records)} |"
    )
    print(f"| Lowest rate-limit headroom seen | {min(headroom) if headroom else 'n/a'} |")
    print(f"| Repos with a gap (more events than one run could fetch) | {len(gap_repos)} |")
    print(f"| Stored events / distinct ids | {total} / {distinct} |")
    print(f"| Repos with saved state | {len(state)} of {loadable} loadable |")
    print("\nEvents per day (last 7 days): " + ", ".join(f"{d} {n}" for d, n in per_day) + "\n")
    print("| Pass criterion | Result |\n| --- | --- |")
    for name, passed in checks.items():
        print(
            f"| {name} | {'PASS' if passed else 'not yet' if 'days elapsed' in name else 'FAIL'} |"
        )
    if failed:
        print("\nFailed runs: " + ", ".join(f"{r['created_at']} ({r['html_url']})" for r in failed))
    by_conclusion = Counter(r["conclusion"] for r in runs)
    print(f"\nRun outcomes: {dict(by_conclusion)}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
