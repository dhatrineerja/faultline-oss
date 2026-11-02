{{ config(severity='warn') }}
-- Freshness: the newest backfill and PyPI snapshots should not be older than 14 days.
select 'backfill' as source, max(snapshot_date) as newest
from {{ ref('stg_gh_repos') }}
having max(snapshot_date) < current_date - 14

union all

select 'pypi', max(snapshot_date)
from {{ ref('stg_pypi_packages') }}
having max(snapshot_date) < current_date - 14
