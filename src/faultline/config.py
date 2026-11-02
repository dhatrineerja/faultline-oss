"""Project settings read from committed config files."""

import csv
from pathlib import Path

PACKAGES_CSV = Path(__file__).resolve().parents[2] / "config" / "packages.csv"


def tracked_repos(path: Path = PACKAGES_CSV) -> list[str]:
    """Lower-case owner/repo names of the tracked set, one entry per repo (monorepos once)."""
    with path.open(encoding="utf-8", newline="") as f:
        return sorted({row["github_repo"].lower() for row in csv.DictReader(f)})
