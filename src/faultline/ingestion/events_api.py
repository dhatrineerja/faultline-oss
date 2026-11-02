"""Fresh job: pull recent events for every tracked repo from the GitHub Events API.

Rows go to the `events_api` table with an event id, type, time, repo and actor, plus tracked_repo (the packages.csv name), in
date-hour partitions. A partition is merged by event id, so re-running never duplicates.
Per-repo ETags and newest-seen times are kept in state/events_api.json so unchanged repos
cost no rate limit.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import pyarrow as pa

from faultline.config import tracked_repos
from faultline.env import load_dotenv
from faultline.lake.store import fetch, lake_dir, partition_path, upload_batch
from faultline.sources.github_events import fetch_events, make_client

TABLE = "events_api"
MIN_RATE_LEFT = 200  # stop early rather than exhaust the hourly limit
WORKERS = 8
SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("type", pa.string()),
        ("created_at", pa.timestamp("us")),
        ("repo_name", pa.string()),
        ("tracked_repo", pa.string()),
        ("actor_login", pa.string()),
        ("payload", pa.string()),
    ]
)


def to_row(event: dict, tracked_repo: str) -> dict:
    # tracked_repo is the name in packages.csv; repo_name is the event's own name, which differs
    # after a rename, and can be missing on some events.
    return {
        "id": str(event["id"]),
        "type": event["type"],
        "created_at": datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
        "repo_name": (event.get("repo") or {}).get("name") or tracked_repo,
        "tracked_repo": tracked_repo,
        "actor_login": (event.get("actor") or {}).get("login"),
        "payload": json.dumps(event.get("payload") or {}, separators=(",", ":")),
    }


def merge_partition(path: Path, rows: list[dict]) -> int:
    """Union rows with the partition's existing rows by id; return rows now stored."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pa.Table.from_pylist(rows, schema=SCHEMA)
    con = duckdb.connect()
    con.register("new_rows", new)
    union = "SELECT * FROM new_rows"
    if path.exists():
        old = f"read_parquet('{path.as_posix()}', hive_partitioning = false)"
        union += f" UNION ALL SELECT * FROM {old}"
    tmp = path.with_suffix(".tmp")
    con.execute(
        f"""COPY (
            SELECT * FROM ({union})
            QUALIFY row_number() OVER (PARTITION BY id ORDER BY created_at) = 1
            ORDER BY created_at, id
        ) TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd)"""
    )
    count = con.execute(f"SELECT count(*) FROM read_parquet('{tmp.as_posix()}')").fetchone()[0]
    con.close()
    tmp.replace(path)
    return count


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def run(root: Path, upload: bool, limit: int | None) -> None:
    state_path = root.parent / "state" / "events_api.json"
    if upload and not state_path.exists():
        fetch("state/events_api.json", root.parent)  # a fresh runner restores the last state
    state = load_state(state_path)
    repos = tracked_repos()[:limit]
    stats = {"changed": 0, "unchanged": 0, "missing": 0, "failed": 0, "skipped": 0, "gaps": 0}
    rows: list[dict] = []
    low_rate = False

    with make_client() as client:

        def work(repo: str):
            if low_rate:
                return repo, None
            s = state.get(repo, {})
            return repo, fetch_events(client, repo, s.get("etag"), s.get("newest"))

        with ThreadPoolExecutor(WORKERS) as pool:
            for repo, res in pool.map(work, repos):
                if res is None:
                    stats["skipped"] += 1
                    continue
                if res.rate_remaining is not None and 0 <= res.rate_remaining < MIN_RATE_LEFT:
                    low_rate = True
                if res.status == 304:
                    stats["unchanged"] += 1
                elif res.status == 404:
                    stats["missing"] += 1
                elif res.status != 200:
                    stats["failed"] += 1
                    print(f"failed {repo}: HTTP {res.status}", file=sys.stderr)
                else:
                    stats["changed"] += 1
                    if res.gap:
                        stats["gaps"] += 1  # more new events than one run could page through
                    rows.extend(to_row(e, repo) for e in res.events)
                    newest = max((e["created_at"] for e in res.events), default=None)
                    state[repo] = {
                        "etag": res.etag,
                        "newest": newest or state.get(repo, {}).get("newest"),
                    }

    groups: dict[tuple[date, int], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["created_at"].date(), row["created_at"].hour), []).append(row)
    uploads: list[tuple[Path, str]] = []
    for (day, hour), part_rows in sorted(groups.items()):
        path = partition_path(root, TABLE, day, hour)
        rel = path.relative_to(root).as_posix()
        if upload and not path.exists():
            fetch(rel, root)  # merge into what is already stored, not into an empty file
        merge_partition(path, part_rows)
        uploads.append((path, rel))

    # State is written last, after the data is safely stored, so a failed run is simply retried.
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    if upload:
        uploads.append((state_path, "state/events_api.json"))
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        upload_batch(uploads, f"events_api {stamp} UTC: {len(rows)} events")
    print(
        f"repos {len(repos)}: {stats}; events {len(rows)} in {len(groups)} partitions",
        file=sys.stderr,
    )
    if low_rate:
        print("stopped early: rate limit nearly exhausted", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--limit", type=int, help="only the first N repos (for testing)")
    args = parser.parse_args()
    load_dotenv()
    run(lake_dir(), upload=not args.no_upload, limit=args.limit)


if __name__ == "__main__":
    main()
