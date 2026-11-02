# Layer 1: Sources

Thin clients for each public source. Public data only.

| Source | Gives | Limit to know | Stage |
| --- | --- | --- | --- |
| GH Archive | Every public GitHub event, hourly files | Large; heavily sampled since October 2025, so history only | 6 |
| GitHub Events API | Recent events per repo, the source of current activity | Rate limited; 300 events or 90 days per repo | 1 |
| GitHub REST or GraphQL API | 6-month backfill of PRs, issues, commits, releases; repo metadata | Rate limited; GraphQL points per hour | 1 |
| PyPI | Releases, project URLs, licence field | Licence field is messy free text | 0, 4 |
| deps.dev | Dependency graph, links, licences | Check terms and quotas before bulk use | 0, 4 |
| OSV | Vulnerability advisories | Coverage varies by ecosystem | 4 |

**Done when** (with ingestion): all three schedules run on time for a week, and rate-limit headroom is logged on every API run.
