from faultline.ingestion.repo_refresh import (
    FLOOR,
    add_waiting,
    reached,
    select_batch,
    since_for,
)


def test_oldest_waiting_repos_are_read_first_and_ties_break_by_name():
    pending = {
        "b/b": "2026-11-09T01:00:00Z",
        "a/a": "2026-11-09T01:00:00Z",
        "c/c": "2026-11-08T23:00:00Z",
    }
    assert select_batch(pending, 2) == ["c/c", "a/a"]


def test_a_repo_keeps_its_earliest_unread_event_time():
    waiting = add_waiting({"a/a": "2026-11-09T05:00:00Z"}, {"a/a": "2026-11-09T09:00:00Z"})
    assert waiting["a/a"] == "2026-11-09T05:00:00Z"
    waiting = add_waiting(waiting, {"b/b": "2026-11-09T10:00:00Z"})
    assert waiting["b/b"] == "2026-11-09T10:00:00Z"


def test_reached_is_just_before_the_earliest_waiting_repo_else_the_watermark():
    assert reached({"a/a": "2026-11-09T05:00:00Z"}, "2026-11-09T12:00:00Z") == "2026-11-09T05:00:00Z"
    assert reached({}, "2026-11-09T12:00:00Z") == "2026-11-09T12:00:00Z"


def test_a_repo_never_read_starts_at_the_floor_then_shortly_before_its_last_read():
    assert since_for("a/a", {}) == FLOOR
    assert since_for("a/a", {"refreshed": {"a/a": "2026-11-09T12:00:00Z"}}) == "2026-11-09T06:00:00Z"
