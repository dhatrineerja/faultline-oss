with src as ({{ with_snapshot('pypi/releases') }})

select
    package,
    version,
    cast(uploaded_at as timestamp) as uploaded_at,
    yanked
from src
where snapshot_date = (select max(snapshot_date) from src)
