-- Distinct people who merged a pull request or published a release in the current window.
-- Merges and releases after the backfill snapshot come from the incremental refresh, merged into
-- the staging models. Triage (labelling or closing) is not in the data, so it is not counted; see
-- the definitions changelog.
select
    c.repo,
    count(distinct e.person) as value
from {{ ref('int_coverage') }} as c
cross join {{ ref('int_params') }} as p
left join {{ ref('int_people_events') }} as e
    on e.repo = c.repo
   and e.kind in ('merge', 'release')
   and e.ts >= p.cur_start and e.ts < p.end_ts
where c.prs_covered_from <= p.cur_start
group by c.repo
