with src as ({{ with_snapshot('pypi/packages') }})

select
    snapshot_date,
    package,
    found,
    inactive,
    latest_version,
    release_count,
    cast(first_release_at as timestamp) as first_release_at,
    cast(last_release_at as timestamp) as last_release_at
from src
where snapshot_date = (select max(snapshot_date) from src)
