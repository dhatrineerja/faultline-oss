import duckdb

from faultline.ingestion.events_api import merge_partition, to_row


def _event(i, created="2026-11-01T13:40:54Z"):
    return {
        "id": str(i),
        "type": "PushEvent",
        "actor": {"login": "a"},
        "repo": {"name": "pallets/flask"},
        "payload": {"size": 1},
        "created_at": created,
    }


def test_merge_is_idempotent_and_adds_new_events(tmp_path):
    path = tmp_path / "part.parquet"
    rows = [to_row(_event(1), "pallets/flask"), to_row(_event(2), "pallets/flask")]
    assert merge_partition(path, rows) == 2
    assert merge_partition(path, rows) == 2  # re-run: same rows, no duplicates
    assert merge_partition(path, [to_row(_event(3), "pallets/flask")]) == 3
    ids = duckdb.sql(f"SELECT id FROM '{path.as_posix()}' ORDER BY id").fetchall()
    assert ids == [("1",), ("2",), ("3",)]
