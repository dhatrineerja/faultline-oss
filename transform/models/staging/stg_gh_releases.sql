with src as ({{ with_snapshot('backfill/releases') }})

select
    tracked_repo as repo,
    tag_name,
    cast(published_at as timestamp) as published_at,
    is_prerelease,
    author
from src
where snapshot_date = (select max(snapshot_date) from src)
