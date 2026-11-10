-- The windows every component is measured over, computed once. end_ts is exclusive: the first
-- instant after the as_of day, so the whole as_of day counts.
--
-- as_of is the last day every live source has fully reached, and never earlier than the day after
-- the backfill snapshot would imply. The sources are the event stream and the incremental refresh
-- (whose reach is the time before which every changed repo has been read again). The as_of
-- variable overrides this, for tests and the backtest.
with snapshot as (
    select cast(max(snapshot_date) as timestamp) + to_days(1) as end_ts
    from {{ ref('stg_gh_repos') }}
),

live as (
    select
        least(
            (select date_trunc('day', max(created_at))
             from read_parquet('{{ lake_dir() }}/events_api/**/*.parquet', hive_partitioning = false)),
            (select date_trunc('day', max(reached_at))
             from read_parquet('{{ lake_dir() }}/refresh_reach/**/*.parquet', hive_partitioning = false))
        ) as reached
),

chosen as (
    select
        coalesce(
            nullif('{{ var("as_of") }}', '')::date,
            cast(greatest(coalesce((select reached from live), (select end_ts from snapshot)),
                          (select end_ts from snapshot)) - to_days(1) as date)
        ) as as_of
)

select
    as_of,
    cast(as_of as timestamp) + to_days(1) as end_ts,
    cast(as_of as timestamp) + to_days(1) - to_days({{ var('window_days') }}) as cur_start,
    cast(as_of as timestamp) + to_days(1) - to_days(2 * {{ var('window_days') }}) as prev_start,
    cast(as_of as timestamp) + to_days(1) - to_days(30) as flow_end
from chosen
