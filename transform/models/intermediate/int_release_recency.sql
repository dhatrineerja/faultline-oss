-- Days since the package's last PyPI release that was not yanked, as of the end of the as_of day.
select
    k.package,
    date_diff('day', k.last_release_at, p.end_ts) as value,
    k.inactive
from {{ ref('stg_pypi_packages') }} as k
cross join {{ ref('int_params') }} as p
where k.found and k.last_release_at is not null and k.last_release_at < p.end_ts
