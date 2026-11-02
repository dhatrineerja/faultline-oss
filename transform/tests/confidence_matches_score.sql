-- A package has a confidence label exactly when it has a score.
select package, score, confidence
from {{ ref('health_score') }}
where (score is null) != (confidence is null)
