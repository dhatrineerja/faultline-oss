from datetime import datetime

from faultline.ingestion.topup import FLOOR, OVERLAP, since_for, to_row


def test_to_row_keeps_the_merger_not_just_the_author():
    node = {
        "number": 7,
        "mergedAt": "2026-11-05T10:00:00Z",
        "updatedAt": "2026-11-05T10:01:00Z",
        "author": {"login": "dependabot"},
        "mergedBy": {"login": "maintainer"},
    }
    row = to_row("o/r", node, datetime(2026, 11, 9))
    assert (row["author"], row["merged_by"], row["number"]) == ("dependabot", "maintainer", 7)


def test_to_row_handles_a_deleted_account():
    node = {
        "number": 1,
        "mergedAt": "2026-11-05T10:00:00Z",
        "updatedAt": "2026-11-05T10:00:00Z",
        "author": None,
        "mergedBy": None,
    }
    assert to_row("o/r", node, datetime(2026, 11, 9))["merged_by"] is None


def test_since_starts_at_the_floor_then_shortly_before_the_last_fetch():
    assert since_for("o/r", {}) == FLOOR
    state = {"fetched": {"o/r": "2026-11-09T12:00:00Z"}}
    assert since_for("o/r", state) == "2026-11-09T06:00:00Z"
    assert OVERLAP.total_seconds() == 6 * 3600
    old = {"fetched": {"o/r": "2026-10-31T01:00:00Z"}}
    assert since_for("o/r", old) == FLOOR  # never earlier than the floor
