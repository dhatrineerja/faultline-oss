"""Bring every score component up to date after the backfill, for the repos that changed.

The events stream says which repos had activity (pull requests, reviews, issues, comments,
pushes, releases) since a repo was last read. This job reads those repos again through the same
GraphQL code as the backfill, but only items updated since the last read, and writes them next
to the backfill instead of over it:
  refresh/<table>/date=YYYY-MM-DD/run-HHMMSS.parquet   same columns as backfill/<table>
  refresh_reach/part.parquet                            one row: events before this are applied
State: state/refresh.json holds the event watermark, the repos still waiting (with the time of
their earliest unread event) and when each repo was last read.

Each run reads at most BATCH repos, oldest waiting first, so the cost per run stays bounded
(about 10 GraphQL points per repo) and a burst of activity is worked off over a few runs. The
dbt staging models merge refresh rows into the backfill by key, newest update wins.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from faultline.env import load_dotenv
from faultline.ingestion.backfill import SCHEMAS, backfill_repo
from faultline.lake.runlog import describe, lake_size, write_run_record
from faultline.lake.store import fetch, lake_dir, upload_batch
from faultline.sources.github_graphql import make_client

TABLE = "refresh"
TABLE_EVENTS = "events_api"
FLOOR = "2026-10-31T00:00:00Z"  # first run reaches back to just before the 1 Nov backfill
OVERLAP = timedelta(hours=6)  # read a little before the last read, so a slow update is kept
STAMP = "%Y-%m-%dT%H:%M:%SZ"
REACH = "refresh_reach"
RELEVANT = (
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "PullRequestReviewCommentEvent",
    "IssuesEvent",
    "IssueCommentEvent",
    "PushEvent",
    "ReleaseEvent",
)
BATCH = 100
WORKERS = 3
MIN_RATE_LEFT = 1500  # leave room for the events job and the dashboard build
REACH_SCHEMA = pa.schema([("reached_at", pa.timestamp("us"))])


def _ts(value: str) -> datetime:
    return datetime.strptime(value, STAMP)


def sync_recent_events(root: Path, watermark: str | None, today: datetime) -> None:
    """Download the event days from the watermark's day to today, so a fresh runner (or a run
    after a gap) sees every event since the watermark, not only the ones it wrote itself."""
    from huggingface_hub import snapshot_download

    from faultline.env import token

    first = _ts(watermark or FLOOR).date()
    days = [first + timedelta(days=i) for i in range((today.date() - first).days + 1)]
    snapshot_download(
        repo_id=token("HF_DATASET_REPO"),
        repo_type="dataset",
        token=token("HF_TOKEN"),
        local_dir=root,
        allow_patterns=[f"{TABLE_EVENTS}/date={d.isoformat()}/**" for d in days],
    )


def since_for(repo: str, state: dict) -> str:
    """Read items updated since shortly before this repo was last read, else since the floor."""
    last = state.get("refreshed", {}).get(repo)
    if last is None:
        return FLOOR
    return max((_ts(last) - OVERLAP).strftime(STAMP), FLOOR)


def select_batch(pending: dict[str, str], limit: int) -> list[str]:
    """The repos waiting longest first; ties by name so the choice is repeatable."""
    return sorted(pending, key=lambda r: (pending[r], r))[:limit]


def reached(pending: dict[str, str], watermark: str | None) -> str | None:
    """Events before this time are applied: just before the earliest repo still waiting."""
    return min(pending.values()) if pending else watermark


def add_waiting(pending: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """Merge newly seen repos into the waiting list, keeping each repo's earliest event time."""
    out = dict(pending)
    for repo, at in new.items():
        out[repo] = min(out[repo], at) if repo in out else at
    return out


def repos_with_events(root: Path, watermark: str | None) -> tuple[dict[str, str], str | None]:
    """Repos with a relevant event after the watermark (earliest such time), and the newest time."""
    events = root / "events_api"
    if not events.exists():
        return {}, watermark
    kinds = ",".join(f"'{k}'" for k in RELEVANT)
    con = duckdb.connect()
    rows = con.execute(
        f"""SELECT tracked_repo, min(created_at) FROM read_parquet(
                '{events.as_posix()}/**/*.parquet', hive_partitioning = false)
            WHERE type IN ({kinds}) AND created_at > ?
            GROUP BY tracked_repo""",
        [_ts(watermark or FLOOR)],
    ).fetchall()
    newest = con.execute(
        f"""SELECT max(created_at) FROM read_parquet(
                '{events.as_posix()}/**/*.parquet', hive_partitioning = false)"""
    ).fetchone()[0]
    con.close()
    out = {r[0]: r[1].strftime(STAMP) for r in rows}
    return out, newest.strftime(STAMP) if newest else watermark


def run_once(root: Path, upload: bool, limit: int, sync: bool) -> tuple[int, int, int | None]:
    """One batch. Returns (repos read, repos still waiting, lowest rate-limit headroom)."""
    state_path = root.parent / "state" / "refresh.json"
    if upload and not state_path.exists():
        fetch("state/refresh.json", root.parent)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    started = datetime.now(UTC)
    if sync:
        sync_recent_events(root, state.get("watermark"), started)
    new, newest = repos_with_events(root, state.get("watermark"))
    pending = add_waiting(state.get("pending", {}), new)
    batch = select_batch(pending, limit)
    rows: dict[str, list[dict]] = {t: [] for t in SCHEMAS}
    done: list[str] = []
    cut_short: list[str] = []
    headroom: list[int] = []
    stop = False

    with make_client() as client:

        def work(repo: str):
            if stop:
                return repo, None
            return repo, backfill_repo(client, repo, since_for(repo, state))

        with ThreadPoolExecutor(WORKERS) as pool:
            for repo, res in pool.map(work, batch):
                if res is None:
                    continue  # not reached: stays waiting
                got, remaining = res
                if remaining is not None:
                    headroom.append(remaining)
                    stop = stop or remaining < MIN_RATE_LEFT
                for table in SCHEMAS:
                    rows[table].extend(got[table])
                done.append(repo)
                if any(r[k] for r in got["repos"] for k in ("prs_truncated", "issues_truncated", "commits_truncated")):
                    cut_short.append(repo)

    for repo in done:
        pending.pop(repo, None)
        state.setdefault("refreshed", {})[repo] = started.strftime(STAMP)
    state["pending"] = pending
    state["watermark"] = newest
    reach_at = reached(pending, newest)

    uploads: list[tuple[Path, str]] = []
    stamp = f"run-{started:%H%M%S}.parquet"
    for table, schema in SCHEMAS.items():
        if not rows[table]:
            continue
        rel = f"{TABLE}/{table}/date={started:%Y-%m-%d}/{stamp}"
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows[table], schema=schema), path, compression="zstd")
        uploads.append((path, rel))
    if reach_at:
        reach_path = root / REACH / "part.parquet"
        reach_path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist([{"reached_at": _ts(reach_at)}], schema=REACH_SCHEMA)
        pq.write_table(table, reach_path, compression="zstd")
        uploads.append((reach_path, f"{REACH}/part.parquet"))
    # State is written last, after the rows are stored, so a failed run is simply retried.
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    record = {
        "started_at": started.strftime(STAMP),
        "repos_read": len(done),
        "repos_waiting": len(pending),
        "cut_short_repos": cut_short,
        "reached_at": reach_at,
        "rows": {t: len(r) for t, r in rows.items()},
        "rate_remaining_min": min(headroom) if headroom else None,
        "stopped_early": stop,
        **(lake_size() if upload else {}),
    }
    record_path, record_rel = write_run_record(root, "repo_refresh", record)
    if upload:
        uploads += [(record_path, record_rel), (state_path, "state/refresh.json")]
        upload_batch(uploads, f"repo refresh {started:%Y-%m-%d %H:%M} UTC: {len(done)} repos")
    print(
        f"read {len(done)} repos, {len(pending)} still waiting, reached {reach_at}; "
        f"{describe(record)}",
        file=sys.stderr,
    )
    return len(done), len(pending), min(headroom) if headroom else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH, help="repos read per run")
    parser.add_argument(
        "--until-done", action="store_true", help="keep going, pausing when the rate limit is low"
    )
    args = parser.parse_args()
    load_dotenv()
    root = lake_dir()
    upload = not args.no_upload
    sync = upload
    while True:
        read, waiting, headroom = run_once(root, upload, args.batch, sync)
        sync = False  # the events were downloaded once; a long catch-up does not need them again
        if not args.until_done or waiting == 0:
            break
        if read == 0 or (headroom is not None and headroom < MIN_RATE_LEFT):
            print("rate limit low; waiting 10 minutes", file=sys.stderr)
            time.sleep(600)


if __name__ == "__main__":
    main()

