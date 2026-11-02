-- The windows every component is measured over, computed once. end_ts is exclusive: the first
-- instant after the as_of day, so the whole as_of day counts.
select
    {{ as_of() }} as as_of,
    cast({{ as_of() }} as timestamp) + to_days(1) as end_ts,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days({{ var('window_days') }}) as cur_start,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days(2 * {{ var('window_days') }}) as prev_start,
    cast({{ as_of() }} as timestamp) + to_days(1) - to_days(30) as flow_end
