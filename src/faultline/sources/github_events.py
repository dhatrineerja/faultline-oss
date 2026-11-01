"""GitHub Events API client: recent public events for one repository.

The endpoint returns at most 300 events from the last 90 days, 100 per page, newest first.
Conditional requests (If-None-Match) that come back 304 do not use rate limit.
"""

import os
from dataclasses import dataclass, field

import httpx

API = "https://api.github.com/repos/{repo}/events"


@dataclass
class EventsResult:
    status: int  # 200 new data, 304 unchanged, 404 repo gone or renamed, other = failure
    events: list[dict] = field(default_factory=list)
    etag: str | None = None
    rate_remaining: int | None = None


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=30,
        follow_redirects=True,  # renamed or moved repos answer 301 to their new location
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def fetch_events(
    client: httpx.Client,
    repo: str,
    etag: str | None = None,
    newer_than: str | None = None,
    max_pages: int = 3,
) -> EventsResult:
    """Fetch pages until one is not full or reaches events at or before newer_than.

    newer_than is the newest created_at already stored for this repo (ISO text sorts correctly).
    The ETag returned is the first page's, which is the one that changes on new activity.
    """
    events: list[dict] = []
    first_etag = None
    remaining = None
    for page in range(1, max_pages + 1):
        headers = {"If-None-Match": etag} if etag and page == 1 else {}
        resp = client.get(
            API.format(repo=repo), params={"per_page": 100, "page": page}, headers=headers
        )
        remaining = int(resp.headers.get("x-ratelimit-remaining", -1))
        if page == 1:
            first_etag = resp.headers.get("etag")
            if resp.status_code != 200:
                return EventsResult(resp.status_code, [], etag, remaining)
        elif resp.status_code != 200:
            break
        batch = resp.json()
        events.extend(batch)
        reached_known = newer_than and batch and batch[-1]["created_at"] <= newer_than
        if len(batch) < 100 or reached_known:
            break
    return EventsResult(200, events, first_etag, remaining)
