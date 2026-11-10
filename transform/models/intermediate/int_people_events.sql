-- One row per person action that counts toward activity or retention. Bots are excluded here,
-- once, so every component downstream sees only people.
select repo, merged_by as person, merged_at as ts, 'merge' as kind
from {{ ref('stg_gh_prs') }}
where merged_at is not null and merged_by is not null and not {{ is_bot('merged_by') }}

union all

select repo, author, published_at, 'release'
from {{ ref('stg_gh_releases') }}
where author is not null and not {{ is_bot('author') }}

union all

select repo, author, merged_at, 'contribution'
from {{ ref('stg_gh_prs') }}
where merged_at is not null and author is not null and not {{ is_bot('author') }}

union all

select repo, person, committed_at, 'contribution'
from {{ ref('stg_gh_commits') }}
where person is not null and not {{ is_bot('coalesce(author_login, author_name)') }}
