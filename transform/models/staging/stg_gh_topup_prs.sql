-- Merged pull requests fetched by the top-up job (src/faultline/ingestion/topup.py) after the
-- backfill snapshot. Each carries the person who merged it, which a merge event does not.
-- A pull request fetched more than once keeps its newest row. Does not exist before the first
-- top-up run, so the model reads an empty table until the lake has one.
select
    tracked_repo as repo,
    number,
    cast(merged_at as timestamp) as merged_at,
    author,
    merged_by,
    cast(fetched_at as timestamp) as fetched_at
from read_parquet('{{ lake_dir() }}/merged_prs/**/*.parquet', hive_partitioning = false)
qualify row_number() over (partition by tracked_repo, number order by fetched_at desc) = 1
