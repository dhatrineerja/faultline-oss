-- Share of pull requests merged or closed within 30 days of being opened. Only PRs opened early
-- enough to have had a full 30 days count (opened in the current window, at least 30 days ago).
select
    pr.repo,
    avg(case when coalesce(pr.merged_at, pr.closed_at) <= pr.created_at + to_days(30)
             then 1.0 else 0.0 end) as value,
    count(*) as n_prs
from {{ ref('stg_gh_prs') }} as pr
join {{ ref('int_coverage') }} as c on c.repo = pr.repo
cross join {{ ref('int_params') }} as p
where pr.created_at >= p.cur_start and pr.created_at < p.flow_end
  and not {{ is_bot('pr.author') }}
  and c.prs_covered_from <= p.cur_start
group by pr.repo
having count(*) >= {{ var('min_prs_for_flow') }}
