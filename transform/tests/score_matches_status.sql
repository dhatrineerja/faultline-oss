-- Only scored and dormant packages have a score; the others must not carry a number.
select package, status, score
from {{ ref('health_score') }}
where (status in ('scored', 'dormant') and score is null)
   or (status in ('insufficient_data', 'unmapped') and score is not null)
