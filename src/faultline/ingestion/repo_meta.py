"""Load each tracked repository's real last-commit date and star count.

The 6-month backfill cannot say when a quiet repo last had a commit, and the backtest needs
"last commit alone" and "stars alone" as fair baselines. One batched GraphQL query covers 50
repos, so the whole list costs about 35 calls. Written as one snapshot per day:
  repo_meta/snapshot=YYYY-MM-DD/part.parquet   one row per tracked repo
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from faultline.config import tracked_repos
from faultline.env import load_dotenv
from faultline.lake.runlog import describe, lake_size, write_run_record
from faultline.lake.store import lake_dir, upload_batch
from faultline.sources.github_graphql import API, make_client

BATCH = 50

SCHEMA = pa.schema(
    [
        ("tracked_repo", pa.string()),
        ("found", pa.bool_()),
        ("name_with_owner", pa.string()),
        ("stargazers", pa.int64()),
        ("is_archived", pa.bool_()),
        ("pushed_at", pa.string()),
        ("last_commit_at", pa.string()),
    ]
)

FIELDS = (
    "nameWithOwner stargazerCount isArchived pushedAt "
    "defaultBranchRef{target{... on Commit{committedDate}}}"
)


def parse(tracked: str, node: dict | None) -> dict:
    """Turn one repository node (or None when GitHub does not know it) into a row."""
    if node is None:
        return {"tracked_repo": tracked, "found": False}
    target = (node.get("defaultBranchRef") or {}).get("target") or {}
    return {
        "tracked_repo": tracked,
        "found": True,
        "name_with_owner": node["nameWithOwner"],
        "stargazers": node["stargazerCount"],
        "is_archived": node["isArchived"],
        "pushed_at": node["pushedAt"],
        "last_commit_at": target.get("committedDate"),  # empty repo: no default branch
    }


def fetch_batch(client: httpx.Client, repos: list[str]) -> tuple[list[dict], int | None]:
    decls = "".join(f"$o{i}:String!,$n{i}:String!," for i in range(len(repos)))
    body = "".join(
        f"r{i}:repository(owner:$o{i},name:$n{i}){{{FIELDS}}} " for i in range(len(repos))
    )
    variables = {}
    for i, repo in enumerate(repos):
        owner, name = repo.split("/")
        variables[f"o{i}"], variables[f"n{i}"] = owner, name
    query = f"query({decls.rstrip(',')}){{rateLimit{{remaining}} {body}}}"
    for _ in range(3):
        try:
            resp = client.post(API, json={"query": query, "variables": variables})
        except httpx.HTTPError:
            continue
        if resp.status_code in (502, 503, 504):
            continue
        resp.raise_for_status()
        data = resp.json()
        other = [e for e in data.get("errors") or [] if e.get("type") != "NOT_FOUND"]
        if other:
            raise RuntimeError(f"GraphQL error: {other}")
        got = data["data"]
        return (
            [parse(repo, got.get(f"r{i}")) for i, repo in enumerate(repos)],
            (got.get("rateLimit") or {}).get("remaining"),
        )
    raise RuntimeError("GitHub GraphQL kept failing")


def run(root: Path, upload: bool) -> None:
    repos = tracked_repos()
    started = datetime.now(UTC)
    snapshot = started.date().isoformat()
    rows, remaining = [], None
    with make_client() as client:
        for i in range(0, len(repos), BATCH):
            batch_rows, remaining = fetch_batch(client, repos[i : i + BATCH])
            rows.extend(batch_rows)
    path = root / "repo_meta" / f"snapshot={snapshot}" / "part.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), tmp, compression="zstd")
    tmp.replace(path)

    missing = [r["tracked_repo"] for r in rows if not r["found"]]
    record = {
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos": len(rows),
        "missing_repos": missing,
        "no_commit_date": sum(r["found"] and not r["last_commit_at"] for r in rows),
        "rate_remaining_min": remaining,
        **(lake_size() if upload else {}),
    }
    record_path, record_rel = write_run_record(root, "repo_meta", record)
    if upload:
        upload_batch(
            [(path, path.relative_to(root).as_posix()), (record_path, record_rel)],
            f"repo meta {snapshot}: {len(rows)} repos",
        )
    print(f"{len(rows)} repos, {len(missing)} not found; {describe(record)}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    run(lake_dir(), upload=not args.no_upload)


if __name__ == "__main__":
    main()
