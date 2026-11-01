"""Build config/packages.csv: top PyPI packages by recent downloads that have a GitHub repo."""

import csv
import re
import sys
from datetime import date
from pathlib import Path

import httpx

TOP_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
PYPI_URL = "https://pypi.org/pypi/{name}/json"
TARGET = 2000
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

GITHUB_RE = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE)
NOT_OWNERS = {"sponsors", "orgs", "topics", "marketplace", "settings", "features", "apps"}
PREFERRED = ("source", "repository", "code", "github", "homepage", "home")


def github_repo(info: dict) -> str | None:
    """Pick owner/repo from PyPI metadata, preferring source-like URL labels."""
    urls = dict(info.get("project_urls") or {})
    urls.setdefault("home", info.get("home_page") or "")
    ranked = sorted(
        urls.items(),
        key=lambda kv: next((i for i, p in enumerate(PREFERRED) if p in kv[0].lower()), 99),
    )
    for _, url in ranked:
        match = GITHUB_RE.search(url or "")
        if match and match.group(1).lower() not in NOT_OWNERS:
            repo = match.group(2).removesuffix(".git")
            return f"{match.group(1)}/{repo}"
    return None


def load_overrides() -> dict[str, str]:
    path = CONFIG_DIR / "repo_overrides.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return {row["package"].lower(): row["github_repo"] for row in csv.DictReader(f)}


def fetch_repo(client: httpx.Client, name: str) -> str | None:
    for _ in range(3):
        try:
            resp = client.get(PYPI_URL.format(name=name))
        except httpx.HTTPError:
            continue
        if resp.status_code == 404:
            return None
        if resp.status_code == 200:
            return github_repo(resp.json()["info"])
    return None


def main() -> None:
    overrides = load_overrides()
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        rows = client.get(TOP_URL).json()["rows"]
        picked: list[tuple[str, str, int]] = []
        for rank, row in enumerate(rows, start=1):
            name = row["project"]
            repo = overrides.get(name.lower()) or fetch_repo(client, name)
            if repo:
                picked.append((name, repo, rank))
            if len(picked) >= TARGET:
                break
            if rank % 200 == 0:
                print(f"checked {rank}, kept {len(picked)}", file=sys.stderr)
    today = date.today().isoformat()
    out = CONFIG_DIR / "packages.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["package", "github_repo", "added_on", "selection_reason"])
        for name, repo, rank in picked:
            writer.writerow([name, repo, today, f"download rank {rank}"])
    print(f"wrote {len(picked)} packages to {out}")


if __name__ == "__main__":
    main()
