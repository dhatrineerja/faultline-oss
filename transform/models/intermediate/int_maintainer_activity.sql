-- Distinct people who merged a pull request or published a release in the live window: the
-- window_days days ending at live_end_ts, which follows the event stream and top-up job past the
-- backfill snapshot (see int_params and int_people_events). Triage (labelling or closing) is not
-- in the backfill data, so it is not counted; see the definitions changelog.
select
    c.repo,
    count(distinct e.person) as value
from {{ ref('int_coverage') }} as c
cross join {{ ref('int_params') }} as p
left join {{ ref('int_people_events') }} as e
    on e.repo = c.repo
   and e.kind in ('merge', 'release')
   and e.ts >= p.live_cur_start and e.ts < p.live_end_ts
where c.prs_covered_from <= p.live_cur_start
group by c.repo
