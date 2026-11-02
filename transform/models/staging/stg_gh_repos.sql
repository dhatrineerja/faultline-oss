with src as ({{ with_snapshot('backfill/repos') }})

select
    snapshot_date,
    tracked_repo as repo,
    name_with_owner,
    is_archived,
    cast(pushed_at as timestamp) as pushed_at,
    prs_truncated,
    issues_truncated,
    commits_truncated
from src
where snapshot_date = (select max(snapshot_date) from src)
