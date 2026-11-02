with src as ({{ with_snapshot('backfill/commits') }})

select
    tracked_repo as repo,
    oid,
    cast(committed_at as timestamp) as committed_at,
    author_login,
    author_name,
    -- a person is the GitHub login, else the commit author name, so unlinked commits still count
    coalesce(author_login, 'name:' || author_name) as person
from src
where snapshot_date = (select max(snapshot_date) from src)
