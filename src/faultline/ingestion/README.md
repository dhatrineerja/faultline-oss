# Layer 2: Ingestion

Job entry points called by GitHub Actions. Load only new data, and filter to tracked repos and needed columns at read time, which removes most of the volume.

| Schedule | Pulls | Stage |
| --- | --- | --- |
| Every 30 min | Events API for tracked repos (`events_api.py`, built in Stage 1) | 1, 3 |
| Daily | GH Archive (`gharchive_daily.py`); recent files are heavily sampled, so not used for current activity | 1 |
| Weekly | deps.dev, OSV, PyPI metadata | 4 |

The 30-minute job gives a fresh but partial picture. The daily run overwrites those same date-hour partitions with complete data, so fast numbers are corrected and never double-counted.

**Done when:** all three schedules run on time for a week, and rate-limit headroom is logged on every API run.
