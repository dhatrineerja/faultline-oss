{{ config(severity='warn') }}
-- Stage 2 checkpoint: a score for at least 95% of the mapped packages.
select
    count(*) filter (where score is not null) * 1.0 / count(*) as share_with_score
from {{ ref('health_score') }}
where status != 'unmapped'
having count(*) filter (where score is not null) * 1.0 / count(*) < 0.95
