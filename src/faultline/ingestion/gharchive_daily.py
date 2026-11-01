"""Daily job: load one UTC day of GH Archive into the lake, keeping only tracked repos.

Each hour is downloaded, filtered at read time by DuckDB, written to its own partition
(replacing any earlier file there) and then the raw download is deleted. Re-running a day
therefore gives identical rows and never duplicates.
"""

import argparse
import csv
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

from faultline.lake.store import EVENTS, lake_dir, partition_path, upload_partition
from faultline.sources.gharchive import download_hour

PACKAGES_CSV = Path(__file__).resolve().parents[3] / "config" / "packages.csv"

# Columns kept from each event. payload stays as JSON text because its shape depends on the
# event type; the dbt staging models parse the parts they need.
SELECT = """
    id,
    type,
    created_at,
    json_extract_string(repo, '$.name') AS repo_name,
    json_extract_string(actor, '$.login') AS actor_login,
    payload::VARCHAR AS payload
"""


def tracked_repos(path: Path = PACKAGES_CSV) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return sorted({row["github_repo"].lower() for row in csv.DictReader(f)})


def filter_hour(raw: Path, out: Path, repos: list[str]) -> int:
    """Write tracked-repo events from a raw hourly file to out as Parquet; return the row count."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    con = duckdb.connect()
    con.execute("CREATE TABLE tracked (name VARCHAR)")
    con.executemany("INSERT INTO tracked VALUES (?)", [(r,) for r in repos])
    con.execute(
        f"""
        COPY (
            SELECT {SELECT}
            FROM read_json(
                ?, format = 'newline_delimited', ignore_errors = true,
                columns = {{id: 'VARCHAR', type: 'VARCHAR', actor: 'JSON', repo: 'JSON',
                           payload: 'JSON', created_at: 'TIMESTAMP'}}
            )
            WHERE lower(json_extract_string(repo, '$.name')) IN (SELECT name FROM tracked)
            ORDER BY created_at, id
        ) TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """,
        [str(raw)],
    )
    count = con.execute(f"SELECT count(*) FROM read_parquet('{tmp.as_posix()}')").fetchone()[0]
    con.close()
    tmp.replace(out)  # replace the partition in one step
    return count


def run_day(day: date, root: Path, upload: bool) -> int:
    repos = tracked_repos()
    total = 0
    work = Path(tempfile.mkdtemp(prefix="gharchive-"))
    try:
        for hour in range(24):
            raw = download_hour(day, hour, work / f"{day}-{hour}.json.gz")
            out = partition_path(root, EVENTS, day, hour)
            rows = filter_hour(raw, out, repos)
            raw.unlink()  # raw downloads are never kept
            if upload:
                upload_partition(out, root)
            total += rows
            print(f"{day} hour {hour:02d}: {rows} rows", file=sys.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="UTC day, default yesterday")
    parser.add_argument("--no-upload", action="store_true", help="write the local lake only")
    args = parser.parse_args()
    day = args.date or (datetime.now(timezone.utc) - timedelta(days=1)).date()
    total = run_day(day, lake_dir(), upload=not args.no_upload)
    print(f"{day}: {total} rows loaded")


if __name__ == "__main__":
    main()
