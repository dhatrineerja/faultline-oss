-- The windows every component is measured over, computed once. end_ts is exclusive: the first
-- instant after the as_of day, so the whole as_of day counts.
--
-- Maintainer activity is the one component kept current after the snapshot: live_end_ts is the
-- start of the newest day that both the event stream and the top-up job have fully reached, and
-- never earlier than end_ts. Every other component keeps the snapshot windows above.
with live as (
    select
        least(
            (select date_trunc('day', max(created_at))
             from read_parquet('{{ lake_dir() }}/events_api/**/*.parquet', hive_partitioning = false)),
            (select date_trunc('day', max(fetched_at)) from {{ ref('stg_gh_topup_prs') }})
        ) as reached
)

select
    {{ as_of() }} as as_of,
    cast({{ as_of() }} as timestamp) + to_days(1) as end_ts,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days({{ var('window_days') }}) as cur_start,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days(2 * {{ var('window_days') }}) as prev_start,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days(30) as flow_end,
    greatest(coalesce((select reached from live), cast({{ as_of() }} as timestamp) + to_days(1)),
             cast({{ as_of() }} as timestamp) + to_days(1)) as live_end_ts,
    greatest(coalesce((select reached from live), cast({{ as_of() }} as timestamp) + to_days(1)),
             cast({{ as_of() }} as timestamp) + to_days(1)) - to_days({{ var('window_days') }})
        as live_cur_start
