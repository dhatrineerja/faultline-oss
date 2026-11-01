# Layer 3: Lake

Date- and hour-partitioned Parquet in a Hugging Face dataset. The lake is the only source of truth; every other store can be rebuilt from it. Raw downloads are deleted after each run.

Writes replace a whole date-hour partition, so a retry never double-counts.

**Built in:** Stage 1.

**Done when:** data is partitioned by date and hour, a re-run overwrites and never duplicates, and total size is tracked.
