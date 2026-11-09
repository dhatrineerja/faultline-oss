"""Keep maintainer activity current between backfills: events say where, GraphQL says who.

A merge event names the pull request's author, not the person who merged it, so events alone
cannot count maintainers. This job reads the merge events that arrived since its last run,
and for each repo that had one, asks GraphQL for the repo's recently merged pull requests,
which carry the real merger. Releases need no top-up: their events carry the author.

Output, append-only (one small file per run, deduplicated by the dbt staging model):
  merged_prs/date=YYYY-MM-DD/run-HHMMSS.parquet   one row per merged pull request fetched
State: state/topup.json holds the newest event already handled, the time each repo was last
fetched, and repos whose fetch failed and must be retried.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from faultline.env import load_dotenv
from faultline.lake.runlog import describe, lake_size, write_run_record
from faultline.lake.store import fetch, lake_dir, upload_batch
from faultline.sources.github_graphql import fetch_merged_prs, make_client

TABLE = "merged_prs"
TABLE_EVENTS = "events_api"
FLOOR = "2026-10-31T00:00:00Z"  # first run reaches back to just before the 1 Nov backfill
OVERLAP = timedelta(hours=6)  # refetch a little before the last fetch, so a slow update is kept
MIN_RATE_LEFT = 600
WORKERS = 4
STAMP = "%Y-%m-%dT%H:%M:%SZ"
SCHEMA = pa.schema(
    [
        ("tracked_repo", pa.string()),
        ("number", pa.int64()),
        ("merged_at", pa.timestamp("us")),
        ("updated_at", pa.timestamp("us")),
        ("author", pa.string()),
        ("merged_by", pa.string()),
        ("fetched_at", pa.timestamp("us")),
    ]
)


def _ts(value: str) -> datetime:
    return datetime.strptime(value, STAMP)


def _login(node: dict | None) -> str | None:
    return (node or {}).get("login")


def to_row(repo: str, node: dict, fetched_at: datetime) -> dict:
    return {
        "tracked_repo": repo,
        "number": node["number"],
        "merged_at": _ts(node["mergedAt"]),
        "updated_at": _ts(node["updatedAt"]),
        "author": _login(node.get("author")),
        "merged_by": _login(node.get("mergedBy")),
        "fetched_at": fetched_at,
    }


def since_for(repo: str, state: dict) -> str:
    """Where this repo's fetch starts: shortly before its last fetch, else the floor."""
    last = state.get("fetched", {}).get(repo)
    if last is None:
        return FLOOR
    return max((_ts(last) - OVERLAP).strftime(STAMP), FLOOR)


def repos_with_new_merges(root: Path, watermark: str | None) -> tuple[list[str], str | None]:
    """Repos with a merge event newer than the watermark, and the newest such event time."""
    events = root / "events_api"
    if not events.exists():
        return [], watermark
    con = duckdb.connect()
    rows = con.execute(
        f"""SELECT tracked_repo, max(created_at) FROM read_parquet(
                '{events.as_posix()}/**/*.parquet', hive_partitioning = false)
            WHERE type = 'PullRequestEvent'
              AND json_extract_string(payload, '$.action') = 'merged'
              AND created_at > ?
            GROUP BY tracked_repo ORDER BY tracked_repo""",
        [_ts(watermark or FLOOR)],
    ).fetchall()
    con.close()
    newest = max((r[1] for r in rows), default=None)
    return [r[0] for r in rows], newest.strftime(STAMP) if newest else watermark


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


def run(root: Path, upload: bool, limit: int | None) -> None:
    state_path = root.parent / "state" / "topup.json"
    if upload and not state_path.exists():
        fetch("state/topup.json", root.parent)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    started = datetime.now(UTC)
    if upload:
        sync_recent_events(root, state.get("watermark"), started)
    new_repos, newest = repos_with_new_merges(root, state.get("watermark"))
    todo = sorted(set(new_repos) | set(state.get("pending", [])))[:limit]
    rows: list[dict] = []
    failed: list[str] = []
    cut_short: list[str] = []
    low_rate = False
    headroom: list[int] = []
    fetched_at = started.replace(tzinfo=None)

    with make_client() as client:

        def work(repo: str):
            if low_rate:
                return repo, None
            return repo, fetch_merged_prs(client, repo, since_for(repo, state))

        with ThreadPoolExecutor(WORKERS) as pool:
            for repo, res in pool.map(work, todo):
                if res is None:
                    failed.append(repo)  # not reached: retry next run
                    continue
                if res.rate_remaining is not None:
                    headroom.append(res.rate_remaining)
                    low_rate = low_rate or res.rate_remaining < MIN_RATE_LEFT
                if res.missing:
                    continue
                if res.truncated:
                    cut_short.append(repo)
                rows.extend(to_row(repo, n, fetched_at) for n in res.nodes if n["mergedAt"])
                state.setdefault("fetched", {})[repo] = started.strftime(STAMP)

    uploads: list[tuple[Path, str]] = []
    if rows:
        rel = f"{TABLE}/date={started:%Y-%m-%d}/run-{started:%H%M%S}.parquet"
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), path, compression="zstd")
        uploads.append((path, rel))
    # State is written last, after the rows are stored, so a failed run is simply retried.
    if limit is None:
        state["watermark"] = newest
    state["pending"] = failed
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    record = {
        "started_at": started.strftime(STAMP),
        "repos_with_new_merges": len(new_repos),
        "repos_fetched": len(todo) - len(failed),
        "merged_prs": len(rows),
        "failed_repos": failed,
        "cut_short_repos": cut_short,
        "rate_remaining_min": min(headroom) if headroom else None,
        "stopped_early": low_rate,
        **(lake_size() if upload else {}),
    }
    record_path, record_rel = write_run_record(root, "topup", record)
    if upload:
        uploads += [(record_path, record_rel), (state_path, "state/topup.json")]
        upload_batch(uploads, f"topup {started:%Y-%m-%d %H:%M} UTC: {len(rows)} merged PRs")
    print(
        f"{len(new_repos)} repos with new merges, {len(todo) - len(failed)} fetched, "
        f"{len(rows)} merged PRs, {len(cut_short)} cut short, {len(failed)} to retry; "
        f"{describe(record)}",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--limit", type=int, help="only the first N repos (testing; keeps state)")
    args = parser.parse_args()
    load_dotenv()
    run(lake_dir(), upload=not args.no_upload, limit=args.limit)


if __name__ == "__main__":
    main()
