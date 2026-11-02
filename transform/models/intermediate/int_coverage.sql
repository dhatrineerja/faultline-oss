-- How far back the backfill reached for each repo and section. A section that hit its page cap
-- holds only the newest items, so any window older than that cannot be measured for the repo.
with oldest as (
    select 'prs' as section, repo, min(updated_at) as oldest from {{ ref('stg_gh_prs') }} group by repo
    union all
    select 'issues', repo, min(updated_at) from {{ ref('stg_gh_issues') }} group by repo
    union all
    select 'commits', repo, min(committed_at) from {{ ref('stg_gh_commits') }} group by repo
),

full_start as (
    select cast(max(snapshot_date) as timestamp) - to_days({{ var('backfill_days') }}) as ts
    from {{ ref('stg_gh_repos') }}
)

select
    r.repo,
    case when r.prs_truncated then coalesce(po.oldest, (select ts from full_start) + to_days(3650))
         else (select ts from full_start) end as prs_covered_from,
    case when r.issues_truncated then coalesce(io.oldest, (select ts from full_start) + to_days(3650))
         else (select ts from full_start) end as issues_covered_from,
    case when r.commits_truncated then coalesce(co.oldest, (select ts from full_start) + to_days(3650))
         else (select ts from full_start) end as commits_covered_from
from {{ ref('stg_gh_repos') }} as r
left join oldest as po on po.repo = r.repo and po.section = 'prs'
left join oldest as io on io.repo = r.repo and io.section = 'issues'
left join oldest as co on co.repo = r.repo and co.section = 'commits'
