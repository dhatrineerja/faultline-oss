"""Measure the pipeline's public claims against live evidence and print a markdown report.

Claims checked (each prints PASS, FAIL or PENDING with the measured numbers):
  C1  The events load runs about every 30 minutes (longest gap under 45 minutes).
  C2  No stretch over 6 hours without a good run for 7 straight days (PENDING until 7 days pass).
  C3  Scores follow the live data: the refresh has reached to within 60 minutes of now.
  C4  The refresh stays inside the free GraphQL allowance (lowest headroom above 1,500 points).
  C5  The newest commit passes CI.

Run from the repository root:
  .venv/Scripts/python ops/verify_claims.py --since 2026-11-09T19:10 [--out docs/claims-evidence.md]
"""

import argparse
import json
import statistics
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import refresh_gaps as gaps

from faultline.env import load_dotenv, token

MAX_GAP_H = 0.75
LAG_LIMIT_MIN = 60
RATE_FLOOR = 1500
WEEK = timedelta(days=7)


def api(path: str) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{gaps.REPO}/{path}",
        headers={"Authorization": f"Bearer {token('GITHUB_TOKEN')}"},
    )
    return json.load(urllib.request.urlopen(req))


def refresh_records(since: datetime) -> list[dict]:
    import os

    from huggingface_hub import HfApi, hf_hub_download

    repo, tok = os.environ["HF_DATASET_REPO"].strip(), os.environ["HF_TOKEN"].strip()
    files = sorted(
        f
        for f in HfApi(token=tok).list_repo_files(repo, repo_type="dataset")
        if f.startswith("metrics/repo_refresh/") and f.endswith(".json")
    )
    out = []
    for f in files:
        path = hf_hub_download(repo, f, repo_type="dataset", token=tok)
        rec = json.loads(Path(path).read_text(encoding="utf-8"))
        if gaps.parse(rec["finished_at"]) >= since:
            out.append(rec)
    return out


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True, help="start of the trigger, UTC")
    parser.add_argument("--out", help="write the report to this file as well")
    args = parser.parse_args()
    load_dotenv()
    since = datetime.fromisoformat(args.since).replace(tzinfo=UTC)
    now = datetime.now(UTC)

    all_runs = gaps.runs_since(since)
    runs = [r for r in all_runs if r["status"] == "completed"]
    # a run still going has already loaded the events (its first step), so its start counts
    running = [gaps.parse(r["created_at"]) for r in all_runs if r["status"] != "completed"]
    ok = [r for r in runs if r["conclusion"] == "success"]
    times = [gaps.parse(r["created_at"]) for r in ok]
    gap_h = [(b - a).total_seconds() / 3600 for a, b in pairwise(times)]
    span = now - times[0]
    longest = max(gap_h)
    # the quiet stretch includes the time since the last success
    open_gap = (now - max(times + running)).total_seconds() / 3600

    recs = refresh_records(since)
    last = recs[-1]
    reached = gaps.parse(last["reached_at"])
    lag_min = (now - reached).total_seconds() / 60
    rates = [r["rate_remaining_min"] for r in recs if r.get("rate_remaining_min") is not None]

    head = api("commits/main")["sha"]
    ci = [r for r in api("actions/workflows/ci.yml/runs?per_page=5")["workflow_runs"]
          if r["head_sha"] == head]

    c1 = (
        f"{len(ok)} of {len(runs)} runs succeeded over {span.total_seconds() / 3600:.1f} h; "
        f"median gap {statistics.median(gap_h):.2f} h, longest {longest:.2f} h, "
        f"time since the newest run started {open_gap:.2f} h (limit {MAX_GAP_H} h)"
    )
    c2 = (
        f"{span.total_seconds() / 86400:.2f} of 7 days measured; "
        f"longest gap so far {longest:.2f} h; earliest pass {(times[0] + WEEK):%Y-%m-%d %H:%M} UTC"
    )
    c3 = (
        f"refresh reached {reached:%Y-%m-%d %H:%M} UTC, {lag_min:.0f} min before now; "
        f"{last['repos_waiting']} repos waiting"
    )
    c4 = (
        f"lowest headroom {min(rates)} points over {len(recs)} refresh runs (floor {RATE_FLOOR}); "
        f"cut-short repos in newest run: {len(last['cut_short_repos'])}"
    )
    c5 = f"commit {head[:7]}: {ci[0]['conclusion'] if ci else 'no run yet'}"
    ci_done = bool(ci) and ci[0]["conclusion"] is not None
    ci_result = "PENDING" if not ci_done else verdict(ci[0]["conclusion"] == "success")
    stuck = longest > 6 or open_gap > 6
    c2_result = "FAIL" if stuck else "PASS" if span >= WEEK else "PENDING"
    rows = [
        ("C1", "Events load about every 30 min", verdict(max(longest, open_gap) <= MAX_GAP_H), c1),
        ("C2", "No gap over 6 h for 7 straight days", c2_result, c2),
        ("C3", f"Scores within {LAG_LIMIT_MIN} min of live data", verdict(lag_min <= LAG_LIMIT_MIN), c3),
        ("C4", "Stays inside the free GraphQL allowance", verdict(bool(rates) and min(rates) >= RATE_FLOOR), c4),
        ("C5", "Newest commit passes CI", ci_result, c5),
    ]
    lines = [
        f"Measured {now:%Y-%m-%d %H:%M} UTC; trigger window starts {since:%Y-%m-%d %H:%M} UTC.\n",
        "| Claim | What it says | Result | Evidence |",
        "| --- | --- | --- | --- |",
        *[f"| {a} | {b} | **{c}** | {d} |" for a, b, c, d in rows],
    ]
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    sys.exit(0 if all(r[2] != "FAIL" for r in rows) else 1)


if __name__ == "__main__":
    main()
