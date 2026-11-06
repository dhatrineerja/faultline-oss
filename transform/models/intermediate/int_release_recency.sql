-- Days since the package's last PyPI release that was not yanked, as of the end of the as_of day.
-- Read from the release list, not the package's latest release, so a release published after
-- the as_of day (the scores are computed for a past day) falls back to the one before it.
with last_release as (
    select r.package, max(r.uploaded_at) as last_release_at
    from {{ ref('stg_pypi_releases') }} as r
    cross join {{ ref('int_params') }} as p
    where not coalesce(r.yanked, false) and r.uploaded_at < p.end_ts
    group by r.package
)

select
    k.package,
    date_diff('day', l.last_release_at, p.end_ts) as value,
    k.inactive
from {{ ref('stg_pypi_packages') }} as k
cross join {{ ref('int_params') }} as p
inner join last_release as l on l.package = k.package
where k.found
