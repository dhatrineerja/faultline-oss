-- Fewest people who made half of the commits. The backfill holds about 6 months of commits, not
-- the 12 months in the definition, so this is measured over what was fetched (see changelog).
-- Bots are excluded; commits with no GitHub login count under the author name. Commits after the
-- as_of day are ignored, so a repo fetched later than the snapshot is scored as of the same day.
with counts as (
    select c.repo, c.person, count(*) as n
    from {{ ref('stg_gh_commits') }} as c
    cross join {{ ref('int_params') }} as p
    where c.person is not null and not {{ is_bot('coalesce(c.author_login, c.author_name)') }}
      and c.committed_at < p.end_ts
    group by c.repo, c.person
),

running as (
    select
        repo,
        n,
        sum(n) over (partition by repo order by n desc, person) as running_total,
        sum(n) over (partition by repo) as total
    from counts
)

select
    repo,
    count(*) filter (where running_total - n < 0.5 * total) as value,
    max(total) as n_commits
from running
group by repo
having max(total) >= {{ var('min_commits_for_bus_factor') }}
