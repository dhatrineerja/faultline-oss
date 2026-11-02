# Layer 1: Sources

Thin clients for each public source. Public data only.

| Source | Gives | Limit to know | Stage |
| --- | --- | --- | --- |
| GitHub Events API | Recent events per repo, the source of current activity | Rate limited; 300 events or 90 days per repo | 1 |
| GitHub REST or GraphQL API | 6-month backfill and backtest history of PRs, issues, commits, releases; repo metadata | Rate limited; GraphQL points per hour; page caps for busy repos | 1, 6 |
| PyPI | Releases, project URLs, licence field | Licence field is messy free text | 0, 4 |
| deps.dev | Dependency graph, links, licences | Check terms and quotas before bulk use | 0, 4 |
| OSV | Vulnerability advisories | Coverage varies by ecosystem | 4 |

**Done when** (with ingestion): all three schedules run on time for a week, and rate-limit headroom is logged on every API run.
