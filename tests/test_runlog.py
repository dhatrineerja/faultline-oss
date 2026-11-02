import json

from faultline.lake.runlog import describe, write_run_record


def test_record_is_written_under_metrics_and_described(tmp_path):
    record = {
        "rate_remaining_min": 1234,
        "gap_repos": ["a/b"],
        "missing_repos": [],
        "failed_repos": [],
    }
    path, rel = write_run_record(tmp_path, "events_api", record)
    assert rel.startswith("metrics/events_api/date=") and rel.endswith(".json")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["job"] == "events_api" and saved["rate_remaining_min"] == 1234
    assert "headroom 1234" in describe(saved) and "gaps 1" in describe(saved)
