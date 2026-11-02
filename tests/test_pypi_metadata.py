from faultline.ingestion.pypi_metadata import parse


def _file(at, yanked=False):
    return {"upload_time_iso_8601": at, "yanked": yanked}


def test_parse_finds_last_release_and_flags_inactive():
    doc = {
        "info": {"version": "2.0", "classifiers": ["Development Status :: 7 - Inactive"]},
        "releases": {
            "1.0": [_file("2020-01-01T00:00:00Z")],
            "2.0": [_file("2021-06-01T00:00:00Z"), _file("2021-06-02T00:00:00Z")],
            "3.0": [_file("2022-01-01T00:00:00Z", yanked=True)],
            "4.0": [],
        },
    }
    row, releases = parse("demo", doc)
    assert row["inactive"] is True
    assert row["release_count"] == 3  # the empty version was never published
    assert row["last_release_at"] == "2021-06-01T00:00:00Z"  # a yanked release does not count
    assert {r["version"] for r in releases} == {"1.0", "2.0", "3.0"}
