import gzip
import json
from pathlib import Path

import duckdb

from faultline.ingestion.gharchive_daily import filter_hour, tracked_repos


def _event(i, repo, kind="PushEvent"):
    return {
        "id": str(i),
        "type": kind,
        "actor": {"login": "someone"},
        "repo": {"name": repo},
        "payload": {"action": "opened", "size": 1},
        "created_at": "2026-10-30T12:00:00Z",
        "public": True,
    }


def _raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw.json.gz"
    events = [_event(1, "Boto/Boto3"), _event(2, "other/repo"), _event(3, "boto/boto3")]
    with gzip.open(raw, "wt", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
    return raw


def test_filter_keeps_only_tracked_repos_case_insensitively(tmp_path):
    out = tmp_path / "part.parquet"
    assert filter_hour(_raw(tmp_path), out, ["boto/boto3"]) == 2
    rows = duckdb.sql(f"SELECT id, repo_name FROM '{out.as_posix()}' ORDER BY id").fetchall()
    assert rows == [("1", "Boto/Boto3"), ("3", "boto/boto3")]


def test_rerun_replaces_partition_with_identical_rows(tmp_path):
    out = tmp_path / "part.parquet"
    raw = _raw(tmp_path)
    first = filter_hour(raw, out, ["boto/boto3"])
    second = filter_hour(raw, out, ["boto/boto3"])
    assert first == second == 2
    assert not out.with_suffix(".tmp").exists()


def test_tracked_repos_file_is_nonempty_and_lowercase():
    repos = tracked_repos()
    assert len(repos) > 1000
    assert all(r == r.lower() for r in repos)
