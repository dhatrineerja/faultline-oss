# Layer 1: Sources

Thin clients for each public source. Public data only.

| Source | Gives | Limit to know | Stage |
| --- | --- | --- | --- |
| GH Archive | Every public GitHub event, hourly files | Large; a few hours of delay | 1 |
| GitHub Events API | Recent events per repo | Rate limited; cannot rebuild history | 3 |
| GitHub REST or GraphQL API | Repo metadata, archived flag, contributors | Rate limited | 3 |
| PyPI | Releases, project URLs, licence field | Licence field is messy free text | 0, 4 |
| deps.dev | Dependency graph, links, licences | Check terms and quotas before bulk use | 0, 4 |
| OSV | Vulnerability advisories | Coverage varies by ecosystem | 4 |

**Done when** (with ingestion): all three schedules run on time for a week, and rate-limit headroom is logged on every API run.
