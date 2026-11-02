with src as ({{ with_snapshot('backfill/prs') }})

select
    tracked_repo as repo,
    number,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(merged_at as timestamp) as merged_at,
    cast(closed_at as timestamp) as closed_at,
    state,
    is_draft,
    author,
    merged_by,
    first_comments,
    first_reviews
from src
where snapshot_date = (select max(snapshot_date) from src)
