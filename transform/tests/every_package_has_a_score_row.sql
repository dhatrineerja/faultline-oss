-- No tracked package may be silently dropped: unmapped ones get a row with status 'unmapped'.
select k.package
from {{ ref('stg_packages') }} as k
left join {{ ref('health_score') }} as h on h.package = k.package
where h.package is null
