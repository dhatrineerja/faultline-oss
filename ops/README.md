# Layer 8: Operations

Alerts on failed jobs, secrets in GitHub, Vercel and Hugging Face settings, and CI that runs dbt tests on every change.

Metrics to watch: run success rate, minutes since the last good load, rows in and out per run, and rate-limit headroom.

**Tools:** [check_stage1.py](check_stage1.py) measures the Stage 1 7-day checkpoint; how to read it is in [docs/stage-1-checkpoint.md](../docs/stage-1-checkpoint.md).

**Built in:** Stage 3.

**Done when:** an alert has been tested, secrets live only in platform settings, and [runbook.md](runbook.md) covers re-running a failed day.
