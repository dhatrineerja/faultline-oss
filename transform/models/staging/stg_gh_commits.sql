-- Commits: the newest backfill snapshot plus the incremental refresh rows, one row per commit.
with backfill as ({{ with_snapshot('backfill/commits') }}),

merged as (
    select * exclude (snapshot_date), 0 as src, '' as filename
    from backfill
    where snapshot_date = (select max(snapshot_date) from backfill)

    union all by name

    select *, 1 as src from ({{ refresh_rows('commits') }})
),

src as (
    select *
    from merged
    qualify row_number() over (
        partition by tracked_repo, oid order by src desc, filename desc
    ) = 1
)

select
    tracked_repo as repo,
    oid,
    cast(committed_at as timestamp) as committed_at,
    author_login,
    author_name,
    -- a person is the GitHub login, else the commit author name, so unlinked commits still count
    coalesce(author_login, 'name:' || author_name) as person
from src
