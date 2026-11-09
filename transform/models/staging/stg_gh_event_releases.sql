-- Releases seen as events, which carry the release author, so they need no top-up. Only
-- published releases count. Events are stored by event id, so each appears once.
{{ config(materialized='table') }}

select
    tracked_repo as repo,
    json_extract_string(payload, '$.release.tag_name') as tag_name,
    cast(json_extract_string(payload, '$.release.published_at') as timestamp) as published_at,
    json_extract_string(payload, '$.release.author.login') as author
from read_parquet('{{ lake_dir() }}/events_api/**/*.parquet', hive_partitioning = false)
where type = 'ReleaseEvent'
  and json_extract_string(payload, '$.action') = 'published'
  and json_extract_string(payload, '$.release.draft') = 'false'
qualify row_number() over (partition by id order by created_at) = 1
