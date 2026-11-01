"""GH Archive client: one gzipped newline-delimited JSON file per hour of public events."""

from datetime import date
from pathlib import Path

import httpx

URL = "https://data.gharchive.org/{day}-{hour}.json.gz"


def hour_url(day: date, hour: int) -> str:
    # GH Archive file names use an unpadded hour: 2026-10-30-0 ... 2026-10-30-23
    return URL.format(day=day.isoformat(), hour=hour)


def download_hour(day: date, hour: int, dest: Path) -> Path:
    """Stream one hourly file to dest. Raises if the file is missing or the request fails."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", hour_url(day, hour), timeout=120, follow_redirects=True) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_bytes(1 << 20):
                f.write(chunk)
    return dest
