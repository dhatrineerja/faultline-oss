-- Share of the previous window's contributors who contributed again in the current window.
-- A contributor is the author of a merged pull request or of a commit. Needs both windows fully
-- covered and at least min_prev_contributors people in the earlier window.
with sets as (
    select
        e.repo,
        e.person,
        bool_or(e.ts >= p.prev_start and e.ts < p.cur_start) as in_prev,
        bool_or(e.ts >= p.cur_start and e.ts < p.end_ts) as in_cur
    from {{ ref('int_people_events') }} as e
    cross join {{ ref('int_params') }} as p
    where e.kind = 'contribution' and e.ts >= p.prev_start and e.ts < p.end_ts
    group by e.repo, e.person
)

select
    s.repo,
    count(*) filter (where in_prev and in_cur) * 1.0 / count(*) filter (where in_prev) as value,
    count(*) filter (where in_prev) as n_prev
from sets as s
join {{ ref('int_coverage') }} as c on c.repo = s.repo
cross join {{ ref('int_params') }} as p
where c.prs_covered_from <= p.prev_start and c.commits_covered_from <= p.prev_start
group by s.repo
having count(*) filter (where in_prev) >= {{ var('min_prev_contributors') }}
