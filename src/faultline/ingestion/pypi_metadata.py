"""Load PyPI release history and status classifiers for every tracked package.

Writes two small tables to the lake, each replaced whole per snapshot date:
  pypi/packages/snapshot=YYYY-MM-DD/part.parquet   one row per package
  pypi/releases/snapshot=YYYY-MM-DD/part.parquet   one row per package version
Release recency and the "deprecated" flag (Development Status :: 7 - Inactive) come from here.
"""

import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from faultline.config import PACKAGES_CSV
from faultline.env import load_dotenv
from faultline.lake.runlog import describe, lake_size, write_run_record
from faultline.lake.store import lake_dir, upload_batch

URL = "https://pypi.org/pypi/{name}/json"
INACTIVE = "Development Status :: 7 - Inactive"
WORKERS = 8

PACKAGES = pa.schema(
    [
        ("package", pa.string()),
        ("found", pa.bool_()),
        ("inactive", pa.bool_()),
        ("latest_version", pa.string()),
        ("release_count", pa.int64()),
        ("first_release_at", pa.string()),
        ("last_release_at", pa.string()),
    ]
)
RELEASES = pa.schema(
    [
        ("package", pa.string()),
        ("version", pa.string()),
        ("uploaded_at", pa.string()),
        ("yanked", pa.bool_()),
    ]
)


def parse(name: str, doc: dict) -> tuple[dict, list[dict]]:
    """Turn one PyPI JSON document into a package row and its release rows."""
    releases = []
    for version, files in (doc.get("releases") or {}).items():
        times = [f["upload_time_iso_8601"] for f in files if f.get("upload_time_iso_8601")]
        if not times:
            continue  # a version with no files was never published
        releases.append(
            {
                "package": name,
                "version": version,
                "uploaded_at": min(times),
                "yanked": all(f.get("yanked") for f in files),
            }
        )
    info = doc.get("info") or {}
    kept = [r["uploaded_at"] for r in releases if not r["yanked"]]
    row = {
        "package": name,
        "found": True,
        "inactive": INACTIVE in (info.get("classifiers") or []),
        "latest_version": info.get("version"),
        "release_count": len(releases),
        "first_release_at": min(kept) if kept else None,
        "last_release_at": max(kept) if kept else None,
    }
    return row, releases


def fetch(client: httpx.Client, name: str) -> tuple[dict, list[dict]]:
    for _ in range(3):
        try:
            resp = client.get(URL.format(name=name))
        except httpx.HTTPError:
            continue
        if resp.status_code == 404:
            break
        if resp.status_code == 200:
            return parse(name, resp.json())
    missing = {"package": name, "found": False, "inactive": False, "release_count": 0}
    return missing, []


def run(root: Path, upload: bool) -> None:
    with PACKAGES_CSV.open(encoding="utf-8", newline="") as f:
        names = [row["package"] for row in csv.DictReader(f)]
    started = datetime.now(UTC)
    snapshot = started.date().isoformat()
    with (
        httpx.Client(timeout=60, follow_redirects=True) as client,
        ThreadPoolExecutor(WORKERS) as pool,
    ):
        results = list(pool.map(lambda n: fetch(client, n), names))
    package_rows = [r for r, _ in results]
    release_rows = [rel for _, rels in results for rel in rels]

    files = []
    for table, rows, schema in (
        ("packages", package_rows, PACKAGES),
        ("releases", release_rows, RELEASES),
    ):
        path = root / "pypi" / table / f"snapshot={snapshot}" / "part.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), tmp, compression="zstd")
        tmp.replace(path)
        files.append((path, path.relative_to(root).as_posix()))

    not_found = [r["package"] for r in package_rows if not r["found"]]
    record = {
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "packages": len(names),
        "releases": len(release_rows),
        "inactive": sum(r["inactive"] for r in package_rows),
        "missing_repos": not_found,
        **(lake_size() if upload else {}),
    }
    record_path, record_rel = write_run_record(root, "pypi_metadata", record)
    if upload:
        upload_batch(
            [*files, (record_path, record_rel)], f"pypi metadata {snapshot}: {len(names)} packages"
        )
    print(
        f"{len(names)} packages, {len(release_rows)} releases, "
        f"{record['inactive']} inactive, {len(not_found)} not found; {describe(record)}",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    run(lake_dir(), upload=not args.no_upload)


if __name__ == "__main__":
    main()
