"""GitHub GraphQL client for the 6-month backfill: PRs, issues, commits and releases per repo.

Each section is paged on its own until it passes the cutoff date or hits a page cap, so one
very busy repository cannot use the whole hourly allowance. Every response carries the
remaining rate limit, which the caller uses to stop early.
"""

import os
from dataclasses import dataclass, field

import httpx

API = "https://api.github.com/graphql"
PAGE_CAP = {"prs": 40, "issues": 40, "commits": 30}  # 2,000 / 2,000 / 3,000 items at most

COMMENTS = "comments(first:3){nodes{createdAt authorAssociation author{login}}}"
REVIEWS = "reviews(first:3){nodes{createdAt authorAssociation author{login}}}"

SECTIONS = {
    "prs": (
        "pullRequests(first:50, after:$after, orderBy:{field:UPDATED_AT, direction:DESC})",
        (
            f"number createdAt updatedAt mergedAt closedAt state isDraft author{{login}} "
            f"mergedBy{{login}} {COMMENTS} {REVIEWS}"
        ),
    ),
    "issues": (
        "issues(first:50, after:$after, orderBy:{field:UPDATED_AT, direction:DESC})",
        f"number createdAt updatedAt closedAt state author{{login}} {COMMENTS}",
    ),
}

QUERY = """
query($owner:String!, $name:String!%(extra_vars)s){
  rateLimit{remaining}
  repository(owner:$owner, name:$name){ %(body)s }
}"""

REPO_BODY = (
    "nameWithOwner isArchived pushedAt "
    "releases(first:20, orderBy:{field:CREATED_AT, direction:DESC})"
    "{nodes{tagName publishedAt isPrerelease author{login}}}"
)


@dataclass
class Section:
    nodes: list[dict] = field(default_factory=list)
    truncated: bool = False
    missing: bool = False
    rate_remaining: int | None = None


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
    )


def _post(client: httpx.Client, query: str, variables: dict) -> tuple[dict | None, int | None]:
    for _ in range(3):
        try:
            resp = client.post(API, json={"query": query, "variables": variables})
        except httpx.HTTPError:
            continue
        if resp.status_code in (502, 503, 504):
            continue
        resp.raise_for_status()
        data = resp.json()
        remaining = ((data.get("data") or {}).get("rateLimit") or {}).get("remaining")
        if data.get("data") and data["data"].get("repository"):
            return data["data"]["repository"], remaining
        errors = data.get("errors") or []
        if any(e.get("type") != "NOT_FOUND" for e in errors):
            raise RuntimeError(
                f"GraphQL error for {variables['owner']}/{variables['name']}: {errors}"
            )
        return None, remaining  # repository not found or no access
    raise RuntimeError("GitHub GraphQL kept failing")


def repo_info(client: httpx.Client, repo: str) -> tuple[dict | None, int | None]:
    owner, name = repo.split("/")
    query = QUERY % {"extra_vars": "", "body": REPO_BODY}
    return _post(client, query, {"owner": owner, "name": name})


def fetch_section(client: httpx.Client, repo: str, kind: str, since: str) -> Section:
    """kind is prs, issues or commits. since is an ISO timestamp; older items are dropped."""
    owner, name = repo.split("/")
    out = Section()
    after = None
    for _ in range(PAGE_CAP[kind]):
        if kind == "commits":
            body = (
                "defaultBranchRef{target{... on Commit{history(since:$since, first:100, "
                "after:$after){pageInfo{hasNextPage endCursor} nodes{oid committedDate "
                "author{name user{login}}}}}}}"
            )
            extra = ", $after:String, $since:GitTimestamp!"
        else:
            connection, fields = SECTIONS[kind]
            body = f"{connection}{{pageInfo{{hasNextPage endCursor}} nodes{{{fields}}}}}"
            extra = ", $after:String"
        variables = {"owner": owner, "name": name, "after": after, "since": since}
        query = QUERY % {"extra_vars": extra, "body": body}
        if kind != "commits":
            variables.pop("since")
        repository, remaining = _post(client, query, variables)
        out.rate_remaining = remaining
        if repository is None:
            out.missing = True
            return out
        if kind == "commits":
            target = (repository.get("defaultBranchRef") or {}).get("target") or {}
            conn = target.get("history") or {"nodes": [], "pageInfo": {"hasNextPage": False}}
        else:
            conn = repository["pullRequests" if kind == "prs" else "issues"]
        nodes = conn["nodes"]
        if kind != "commits":
            old = [n for n in nodes if n["updatedAt"] < since]
            nodes = [n for n in nodes if n["updatedAt"] >= since]
            if old:  # sorted newest-updated first, so everything after this is older still
                out.nodes.extend(nodes)
                return out
        out.nodes.extend(nodes)
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        after = conn["pageInfo"]["endCursor"]
    out.truncated = True
    return out
