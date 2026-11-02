{#- Where the lake lives: the DBT_LAKE_DIR environment variable, else the lake_dir variable,
    relative to this transform/ folder. CI points DBT_LAKE_DIR at a downloaded copy. -#}
{% macro lake_dir() -%}
{{ env_var('DBT_LAKE_DIR', var('lake_dir')) }}
{%- endmacro %}

{#- All rows of a lake table with the snapshot folder date added, for picking the newest. -#}
{% macro with_snapshot(folder) -%}
select
    * exclude (filename),
    cast(regexp_extract(filename, 'snapshot=([0-9-]+)', 1) as date) as snapshot_date
from read_parquet('{{ lake_dir() }}/{{ folder }}/**/*.parquet', hive_partitioning = false, filename = true)
{%- endmacro %}
