-- Median hours from an issue or pull request being opened to the first reply by a maintainer.
-- A maintainer is an OWNER, MEMBER or COLLABORATOR who is not the author and not a bot. Only the
-- first three comments and reviews were fetched, so an item whose first maintainer reply came
-- later is left out, which makes this slightly optimistic. Only items opened in the current
-- window count. Replies after the as_of day are ignored, so a repo fetched later than the
-- snapshot is measured as of the same day.
with items as (
    select repo, 'pr' as kind, number, author, created_at, first_comments as replies
    from {{ ref('stg_gh_prs') }}
    union all
    select repo, 'pr', number, author, created_at, first_reviews from {{ ref('stg_gh_prs') }}
    union all
    select repo, 'issue', number, author, created_at, first_comments from {{ ref('stg_gh_issues') }}
),

replies as (
    select
        i.repo,
        i.kind,
        i.number,
        i.created_at,
        i.author,
        unnest(json_transform(i.replies, '[{"at":"VARCHAR","assoc":"VARCHAR","by":"VARCHAR"}]')) as r
    from items as i
    cross join {{ ref('int_params') }} as p
    where i.created_at >= p.cur_start and i.created_at < p.end_ts and i.replies != '[]'
),

first_reply as (
    select
        repo,
        kind,
        number,
        min(date_diff('second', created_at, cast(r.at as timestamp))) / 3600.0 as hours
    from replies
    where r.assoc in ('OWNER', 'MEMBER', 'COLLABORATOR')
      and r.by is not null and r.by != author
      and not {{ is_bot('r.by') }}
      and cast(r.at as timestamp) >= created_at
      and cast(r.at as timestamp) < (select end_ts from {{ ref('int_params') }})
    group by repo, kind, number
)

select
    f.repo,
    median(f.hours) as value,
    count(*) as n_items
from first_reply as f
join {{ ref('int_coverage') }} as c on c.repo = f.repo
cross join {{ ref('int_params') }} as p
where c.prs_covered_from <= p.cur_start and c.issues_covered_from <= p.cur_start
group by f.repo
having count(*) >= {{ var('min_items_for_responsiveness') }}
