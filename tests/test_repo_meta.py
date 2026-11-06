from faultline.ingestion.repo_meta import parse


def test_parse_reads_last_commit_and_stars():
    node = {
        "nameWithOwner": "Owner/Repo",
        "stargazerCount": 42,
        "isArchived": False,
        "pushedAt": "2026-10-01T00:00:00Z",
        "defaultBranchRef": {"target": {"committedDate": "2026-09-30T12:00:00Z"}},
    }
    row = parse("owner/repo", node)
    assert row["found"] is True
    assert row["last_commit_at"] == "2026-09-30T12:00:00Z"
    assert row["stargazers"] == 42


def test_parse_handles_unknown_repo_and_empty_repo():
    assert parse("gone/repo", None) == {"tracked_repo": "gone/repo", "found": False}
    empty = {
        "nameWithOwner": "a/b",
        "stargazerCount": 0,
        "isArchived": False,
        "pushedAt": None,
        "defaultBranchRef": None,
    }
    assert parse("a/b", empty)["last_commit_at"] is None
