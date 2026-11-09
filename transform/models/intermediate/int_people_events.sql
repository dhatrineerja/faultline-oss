-- One row per person action that counts toward activity or retention. Bots are excluded here,
-- once, so every component downstream sees only people.
--
-- Merges and releases after the backfill snapshot come from two live sources, each added only
-- for items the backfill does not already hold (same repo and PR number, or same repo and tag),
-- so a repo fetched again later is never counted twice:
--   top-up pull requests   carry the real merger (an event's actor is usually the author)
--   release events         carry the release author
-- Contributions (retention, bus factor) are not topped up; those components stay at the snapshot.
select repo, merged_by as person, merged_at as ts, 'merge' as kind
from {{ ref('stg_gh_prs') }}
where merged_at is not null and merged_by is not null and not {{ is_bot('merged_by') }}

union all

select t.repo, t.merged_by, t.merged_at, 'merge'
from {{ ref('stg_gh_topup_prs') }} as t
where t.merged_at is not null and t.merged_by is not null and not {{ is_bot('t.merged_by') }}
  and not exists (
      select 1 from {{ ref('stg_gh_prs') }} as b
      where b.repo = t.repo and b.number = t.number and b.merged_at is not null
  )

union all

select repo, author, published_at, 'release'
from {{ ref('stg_gh_releases') }}
where author is not null and not {{ is_bot('author') }}

union all

select e.repo, e.author, e.published_at, 'release'
from {{ ref('stg_gh_event_releases') }} as e
where e.author is not null and not {{ is_bot('e.author') }}
  and not exists (
      select 1 from {{ ref('stg_gh_releases') }} as b
      where b.repo = e.repo and b.tag_name = e.tag_name
  )

union all

select repo, author, merged_at, 'contribution'
from {{ ref('stg_gh_prs') }}
where merged_at is not null and author is not null and not {{ is_bot('author') }}

union all

select repo, person, committed_at, 'contribution'
from {{ ref('stg_gh_commits') }}
where person is not null and not {{ is_bot('coalesce(author_login, author_name)') }}
