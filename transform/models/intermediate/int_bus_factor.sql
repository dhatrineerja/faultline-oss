-- Fewest people who made half of the commits. The backfill holds about 6 months of commits, not
-- the 12 months in the definition, so this is measured over what was fetched (see changelog).
-- Bots are excluded; commits with no GitHub login count under the author name.
with counts as (
    select repo, person, count(*) as n
    from {{ ref('stg_gh_commits') }}
    where person is not null and not {{ is_bot('coalesce(author_login, author_name)') }}
    group by repo, person
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
