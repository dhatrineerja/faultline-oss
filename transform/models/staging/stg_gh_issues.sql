-- Issues: the newest backfill snapshot, with the incremental refresh rows merged in; the row
-- with the newest updated_at wins (a later run wins a tie).
with backfill as ({{ with_snapshot('backfill/issues') }}),

merged as (
    select * exclude (snapshot_date), 0 as src, '' as filename
    from backfill
    where snapshot_date = (select max(snapshot_date) from backfill)

    union all by name

    select *, 1 as src from ({{ refresh_rows('issues') }})
),

src as (
    select *
    from merged
    qualify row_number() over (
        partition by tracked_repo, number order by updated_at desc, src desc, filename desc
    ) = 1
)

select
    tracked_repo as repo,
    number,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(closed_at as timestamp) as closed_at,
    state,
    author,
    first_comments
from src
