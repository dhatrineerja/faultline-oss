-- One row per repo from the newest backfill snapshot. The archived flag and push time come from
-- the newest incremental refresh row when there is one. The truncation flags always come from the
-- backfill: they describe how far back its own fetch reached, which the refresh does not change.
with src as ({{ with_snapshot('backfill/repos') }}),

base as (
    select * from src where snapshot_date = (select max(snapshot_date) from src)
),

latest as (
    select *
    from ({{ refresh_rows('repos') }})
    qualify row_number() over (partition by tracked_repo order by filename desc) = 1
)

select
    b.snapshot_date,
    b.tracked_repo as repo,
    coalesce(l.name_with_owner, b.name_with_owner) as name_with_owner,
    coalesce(l.is_archived, b.is_archived) as is_archived,
    cast(coalesce(l.pushed_at, b.pushed_at) as timestamp) as pushed_at,
    b.prs_truncated,
    b.issues_truncated,
    b.commits_truncated
from base as b
left join latest as l on l.tracked_repo = b.tracked_repo
