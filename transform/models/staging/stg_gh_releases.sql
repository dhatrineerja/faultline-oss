-- Releases: the newest backfill snapshot plus the incremental refresh rows, one row per tag.
with backfill as ({{ with_snapshot('backfill/releases') }}),

merged as (
    select * exclude (snapshot_date), 0 as src, '' as filename
    from backfill
    where snapshot_date = (select max(snapshot_date) from backfill)

    union all by name

    select *, 1 as src from ({{ refresh_rows('releases') }})
),

src as (
    select *
    from merged
    qualify row_number() over (
        partition by tracked_repo, tag_name order by src desc, filename desc
    ) = 1
)

select
    tracked_repo as repo,
    tag_name,
    cast(published_at as timestamp) as published_at,
    is_prerelease,
    author
from src
