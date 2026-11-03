"""One-time 6-month backfill of PRs, issues, commits and releases from the GitHub GraphQL API.

Repos are handled in shards of 50 (sorted list). A shard writes one Parquet file per table, so
re-running a shard overwrites it and never duplicates. Completed shards are recorded in
state/backfill.json and skipped, so the job can be re-run each hour until the rate limit has
let every shard through. It stops between shards when the remaining allowance is low.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from faultline.config import tracked_repos
from faultline.env import load_dotenv
from faultline.lake.store import fetch, lake_dir, upload_batch
from faultline.sources.github_graphql import fetch_section, make_client, repo_info

SHARD_SIZE = 50
MIN_RATE_LEFT = 600  # a shard of 50 busy repos can cost several hundred points
WORKERS = 6
WINDOW_DAYS = 183
# Second pass for the repos that hit the normal page cap (pandas, torch, airflow and similar).
DEEP_PAGE_CAP = {"prs": 400, "issues": 400, "commits": 300}  # 20,000 / 20,000 / 30,000 items
DEEP_WORKERS = 3
DEEP_MIN_RATE_LEFT = 1500  # a very busy repo can cost over a thousand points on its own

SCHEMAS = {
    "repos": pa.schema(
        [
            ("tracked_repo", pa.string()),
            ("name_with_owner", pa.string()),
            ("is_archived", pa.bool_()),
            ("pushed_at", pa.string()),
            ("prs_truncated", pa.bool_()),
            ("issues_truncated", pa.bool_()),
            ("commits_truncated", pa.bool_()),
        ]
    ),
    "prs": pa.schema(
        [
            ("tracked_repo", pa.string()),
            ("number", pa.int64()),
            ("created_at", pa.string()),
            ("updated_at", pa.string()),
            ("merged_at", pa.string()),
            ("closed_at", pa.string()),
            ("state", pa.string()),
            ("is_draft", pa.bool_()),
            ("author", pa.string()),
            ("merged_by", pa.string()),
            ("first_comments", pa.string()),  # JSON text; the dbt staging model parses it
            ("first_reviews", pa.string()),
        ]
    ),
    "issues": pa.schema(
        [
            ("tracked_repo", pa.string()),
            ("number", pa.int64()),
            ("created_at", pa.string()),
            ("updated_at", pa.string()),
            ("closed_at", pa.string()),
            ("state", pa.string()),
            ("author", pa.string()),
            ("first_comments", pa.string()),
        ]
    ),
    "commits": pa.schema(
        [
            ("tracked_repo", pa.string()),
            ("oid", pa.string()),
            ("committed_at", pa.string()),
            ("author_login", pa.string()),
            ("author_name", pa.string()),
        ]
    ),
    "releases": pa.schema(
        [
            ("tracked_repo", pa.string()),
            ("tag_name", pa.string()),
            ("published_at", pa.string()),
            ("is_prerelease", pa.bool_()),
            ("author", pa.string()),
        ]
    ),
}


def _login(node: dict | None) -> str | None:
    return (node or {}).get("login")


def _comments(node: dict | None) -> str:
    items = [
        {"at": n["createdAt"], "assoc": n["authorAssociation"], "by": _login(n["author"])}
        for n in ((node or {}).get("nodes") or [])
    ]
    return json.dumps(items, separators=(",", ":"))


def backfill_repo(
    client, repo: str, since: str, caps: dict[str, int] | None = None
) -> tuple[dict[str, list[dict]], int | None]:
    caps = caps or {}
    rows: dict[str, list[dict]] = {t: [] for t in SCHEMAS}
    info, remaining = repo_info(client, repo)
    if info is None:
        return rows, remaining
    prs = fetch_section(client, repo, "prs", since, caps.get("prs"))
    issues = fetch_section(client, repo, "issues", since, caps.get("issues"))
    commits = fetch_section(client, repo, "commits", since, caps.get("commits"))
    rows["repos"].append(
        {
            "tracked_repo": repo,
            "name_with_owner": info["nameWithOwner"],
            "is_archived": info["isArchived"],
            "pushed_at": info["pushedAt"],
            "prs_truncated": prs.truncated,
            "issues_truncated": issues.truncated,
            "commits_truncated": commits.truncated,
        }
    )
    for n in prs.nodes:
        rows["prs"].append(
            {
                "tracked_repo": repo,
                "number": n["number"],
                "created_at": n["createdAt"],
                "updated_at": n["updatedAt"],
                "merged_at": n["mergedAt"],
                "closed_at": n["closedAt"],
                "state": n["state"],
                "is_draft": n["isDraft"],
                "author": _login(n["author"]),
                "merged_by": _login(n["mergedBy"]),
                "first_comments": _comments(n["comments"]),
                "first_reviews": _comments(n["reviews"]),
            }
        )
    for n in issues.nodes:
        rows["issues"].append(
            {
                "tracked_repo": repo,
                "number": n["number"],
                "created_at": n["createdAt"],
                "updated_at": n["updatedAt"],
                "closed_at": n["closedAt"],
                "state": n["state"],
                "author": _login(n["author"]),
                "first_comments": _comments(n["comments"]),
            }
        )
    for n in commits.nodes:
        author = n.get("author") or {}
        rows["commits"].append(
            {
                "tracked_repo": repo,
                "oid": n["oid"],
                "committed_at": n["committedDate"],
                "author_login": _login(author.get("user")),
                "author_name": author.get("name"),
            }
        )
    for n in info["releases"]["nodes"]:
        rows["releases"].append(
            {
                "tracked_repo": repo,
                "tag_name": n["tagName"],
                "published_at": n["publishedAt"],
                "is_prerelease": n["isPrerelease"],
                "author": _login(n["author"]),
            }
        )
    remaining_after = min(
        r
        for r in (remaining, prs.rate_remaining, issues.rate_remaining, commits.rate_remaining)
        if r is not None
    )
    return rows, remaining_after


def write_shard(root: Path, snapshot: str, shard: int, rows: dict[str, list[dict]]) -> list[Path]:
    paths = []
    for table, schema in SCHEMAS.items():
        path = root / "backfill" / table / f"snapshot={snapshot}" / f"shard-{shard:04d}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        pq.write_table(pa.Table.from_pylist(rows[table], schema=schema), tmp, compression="zstd")
        tmp.replace(path)
        paths.append(path)
    return paths


def shard_path(root: Path, snapshot: str, table: str, shard: int) -> Path:
    return root / "backfill" / table / f"snapshot={snapshot}" / f"shard-{shard:04d}.parquet"


def replace_repos(
    old: dict[str, list[dict]], new: dict[str, list[dict]], repos: set[str]
) -> dict[str, list[dict]]:
    """Drop every row of the given repos from a shard and put the fresh rows in their place."""
    return {t: [r for r in old[t] if r["tracked_repo"] not in repos] + new[t] for t in SCHEMAS}


def truncated_repos(root: Path, snapshot: str) -> list[str]:
    out = []
    for path in sorted(shard_path(root, snapshot, "repos", 0).parent.glob("shard-*.parquet")):
        for r in pq.read_table(path).to_pylist():
            if r["prs_truncated"] or r["issues_truncated"] or r["commits_truncated"]:
                out.append(r["tracked_repo"])
    return out


def deepen(root: Path, upload: bool = False) -> None:
    """Re-fetch the repos that hit the page cap with a much higher cap and swap their rows in."""
    state_path = root.parent / "state" / "backfill.json"
    deep_path = root.parent / "state" / "backfill_deep.json"
    if upload:
        for p in (state_path, deep_path):
            if not p.exists():
                fetch(f"state/{p.name}", root.parent)  # False on a first run: no deep state yet
    state = json.loads(state_path.read_text(encoding="utf-8"))
    snapshot, since = state["snapshot"], state["since"]
    deep = json.loads(deep_path.read_text(encoding="utf-8")) if deep_path.exists() else {}
    done = set(deep.get("done", []))
    order = {r: i for i, r in enumerate(tracked_repos())}
    todo = [r for r in truncated_repos(root, snapshot) if r not in done]
    print(f"{len(done)} repos already deepened; {len(todo)} to do", file=sys.stderr)

    with make_client() as client:
        for start in range(0, len(todo), DEEP_WORKERS):
            batch = todo[start : start + DEEP_WORKERS]
            with ThreadPoolExecutor(DEEP_WORKERS) as pool:
                results = list(
                    pool.map(lambda r: backfill_repo(client, r, since, DEEP_PAGE_CAP), batch)
                )
            fetched = {
                r: rows for r, (rows, _) in zip(batch, results, strict=True) if rows["repos"]
            }
            by_shard: dict[int, list[str]] = {}
            for repo in fetched:
                by_shard.setdefault(order[repo] // SHARD_SIZE, []).append(repo)
            for shard, repos in by_shard.items():
                old = {
                    t: pq.read_table(shard_path(root, snapshot, t, shard)).to_pylist()
                    for t in SCHEMAS
                }
                new = {t: [x for r in repos for x in fetched[r][t]] for t in SCHEMAS}
                paths = write_shard(root, snapshot, shard, replace_repos(old, new, set(repos)))
                if upload:
                    items = [(p, p.relative_to(root).as_posix()) for p in paths]
                    upload_batch(items, f"deepen shard {shard}")
            done.update(batch)
            deep_path.write_text(json.dumps({"done": sorted(done)}), encoding="utf-8")
            if upload:
                upload_batch([(deep_path, "state/backfill_deep.json")], "deepen state")
            remaining = min((r for _, r in results if r is not None), default=None)
            for repo, f in fetched.items():
                flags = f["repos"][0]
                print(
                    f"{repo}: {len(f['prs'])} PRs, {len(f['issues'])} issues, "
                    f"{len(f['commits'])} commits; still cut short: "
                    f"{[k for k in ('prs', 'issues', 'commits') if flags[k + '_truncated']]}",
                    file=sys.stderr,
                )
            print(f"allowance left {remaining}", file=sys.stderr)
            if remaining is not None and remaining < DEEP_MIN_RATE_LEFT:
                print("stopped: allowance low; re-run after it resets", file=sys.stderr)
                return
    print("all truncated repos deepened")


def run(root: Path, limit_shards: int | None, upload: bool = False) -> None:
    now = datetime.now(UTC)
    snapshot = now.date().isoformat()
    since = (now - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state_path = root.parent / "state" / "backfill.json"
    if upload and not state_path.exists():
        fetch("state/backfill.json", root.parent)  # a fresh runner restores the last state
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if state.get("snapshot") != snapshot and state.get("done"):
        print(f"previous backfill was {state['snapshot']}; delete {state_path} to start a new one")
        return
    state.setdefault("snapshot", snapshot)
    state.setdefault("since", since)
    state.setdefault("done", [])
    snapshot, since = state["snapshot"], state["since"]  # a resumed run keeps its own window

    repos = tracked_repos()
    shards = [repos[i : i + SHARD_SIZE] for i in range(0, len(repos), SHARD_SIZE)]
    todo = [i for i in range(len(shards)) if i not in state["done"]][:limit_shards]
    print(f"{len(state['done'])}/{len(shards)} shards done; running {len(todo)}", file=sys.stderr)

    with make_client() as client:
        for i in todo:
            with ThreadPoolExecutor(WORKERS) as pool:
                results = list(pool.map(lambda r: backfill_repo(client, r, since), shards[i]))
            merged: dict[str, list[dict]] = {t: [] for t in SCHEMAS}
            for rows, _ in results:
                for table in SCHEMAS:
                    merged[table].extend(rows[table])
            paths = write_shard(root, snapshot, i, merged)
            if upload:  # data first, then state, so a failed upload leaves the shard to be redone
                items = [(p, p.relative_to(root).as_posix()) for p in paths]
                upload_batch(items, f"backfill shard {i}")
            state["done"].append(i)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            if upload:
                upload_batch(
                    [(state_path, "state/backfill.json")], f"backfill state after shard {i}"
                )
            remaining = min((r for _, r in results if r is not None), default=None)
            print(
                f"shard {i}: {len(merged['prs'])} PRs, {len(merged['issues'])} issues, "
                f"{len(merged['commits'])} commits; allowance left {remaining}",
                file=sys.stderr,
            )
            if remaining is not None and remaining < MIN_RATE_LEFT:
                print("stopped: allowance low; re-run after it resets", file=sys.stderr)
                return
    print("all shards done" if len(state["done"]) == len(shards) else "partial; re-run later")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-shards", type=int, help="process at most N shards (testing)")
    parser.add_argument(
        "--deepen", action="store_true", help="second pass for repos that hit the page cap"
    )
    parser.add_argument("--upload", action="store_true", help="also commit to the HF dataset")
    args = parser.parse_args()
    load_dotenv()
    if args.deepen:
        deepen(lake_dir(), args.upload)
    else:
        run(lake_dir(), args.limit_shards, args.upload)


if __name__ == "__main__":
    main()
