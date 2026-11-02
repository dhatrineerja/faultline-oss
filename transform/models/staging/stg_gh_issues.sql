with src as ({{ with_snapshot('backfill/issues') }})

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
where snapshot_date = (select max(snapshot_date) from src)
