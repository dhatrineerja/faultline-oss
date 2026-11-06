-- A package that PyPI knows and that has a release before the as_of day must have a recency value.
select k.package
from {{ ref('stg_pypi_packages') }} as k
cross join {{ ref('int_params') }} as p
left join {{ ref('int_release_recency') }} as r on r.package = k.package
where k.found and r.package is null
  and exists (
      select 1 from {{ ref('stg_pypi_releases') }} as x
      where x.package = k.package and not coalesce(x.yanked, false) and x.uploaded_at < p.end_ts
  )
