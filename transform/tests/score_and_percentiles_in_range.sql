-- Scores and every percentile must lie between 0 and 100.
select package
from {{ ref('health_score') }}
where score not between 0 and 100
   or pct_maintainer_activity not between 0 and 100
   or pct_contributor_retention not between 0 and 100
   or pct_responsiveness not between 0 and 100
   or pct_pr_flow not between 0 and 100
   or pct_release_recency not between 0 and 100
   or pct_bus_factor not between 0 and 100
