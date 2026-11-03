import pyarrow.parquet as pq

from faultline.ingestion.backfill import SCHEMAS, _comments, write_shard


def test_comments_are_flattened_to_json():
    node = {"nodes": [{"createdAt": "t", "authorAssociation": "MEMBER", "author": {"login": "a"}}]}
    assert _comments(node) == '[{"at":"t","assoc":"MEMBER","by":"a"}]'
    assert _comments(None) == "[]"


def test_write_shard_overwrites_rather_than_appends(tmp_path):
    row = {
        "tracked_repo": "a/b",
        "tag_name": "v1",
        "published_at": None,
        "is_prerelease": False,
        "author": None,
    }
    empty = {t: [] for t in SCHEMAS}
    for _ in range(2):
        write_shard(tmp_path, "2026-11-01", 0, {**empty, "releases": [row]})
    files = list((tmp_path / "backfill" / "releases").rglob("*.parquet"))
    assert len(files) == 1
    assert pq.read_table(files[0]).num_rows == 1


def test_replace_repos_swaps_only_the_named_repos():
    from faultline.ingestion.backfill import SCHEMAS, replace_repos

    old = {t: [] for t in SCHEMAS}
    old["prs"] = [{"tracked_repo": "a/a", "number": 1}, {"tracked_repo": "b/b", "number": 2}]
    new = {t: [] for t in SCHEMAS}
    new["prs"] = [{"tracked_repo": "a/a", "number": 1}, {"tracked_repo": "a/a", "number": 3}]
    merged = replace_repos(old, new, {"a/a"})
    assert sorted((r["tracked_repo"], r["number"]) for r in merged["prs"]) == [
        ("a/a", 1),
        ("a/a", 3),
        ("b/b", 2),
    ]
