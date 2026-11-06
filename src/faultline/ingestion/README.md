# Layer 2: Ingestion

Job entry points called by GitHub Actions. Load only new data, and filter to tracked repos and needed columns at read time, which removes most of the volume.

| Schedule | Pulls | Stage |
| --- | --- | --- |
| Every 30 min | Events API for tracked repos (`events_api.py`), via `.github/workflows/refresh.yml` | 1 |
| Once, then on gaps | 6-month GraphQL backfill (`backfill.py`): PRs, issues, commits, releases | 1 |
| Weekly | Last-commit date and stars per repo (`repo_meta.py`) | 3 |
| Weekly | PyPI release history and Inactive flags (`pypi_metadata.py`) | 2 |
| Daily | GitHub REST metadata such as the archived flag | 3 |
| Stage 6 | GraphQL history by date range for the backtest cutoffs | 6 |
| Weekly | deps.dev, OSV, PyPI metadata | 4 |

The Events API returns at most 300 events or 90 days per repo, so the 6-month backfill fills the window at launch and any gap after a long outage. Events are merged into date-hour partitions by id and per-repo state advances only after the data is stored, so a retry never double-counts or loses events.

**Done when:** all three schedules run on time for a week, and rate-limit headroom is logged on every API run.
