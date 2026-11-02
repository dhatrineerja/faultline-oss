{#- True for bot accounts. GraphQL returns bot logins without the [bot] suffix, so a name list
    (seeds/bots.csv) is used as well as the suffix rules. Missing logins count as not a bot. -#}
{% macro is_bot(login) -%}
(
    lower({{ login }}) like '%[bot]'
    or lower({{ login }}) like '%-bot'
    or lower({{ login }}) like 'gh-worker-%'
    or lower({{ login }}) in (select name from {{ ref('bots') }})
)
{%- endmacro %}

{#- The date scores are computed for: the as_of variable, else the newest backfill snapshot. -#}
{% macro as_of() -%}
coalesce(
    nullif('{{ var("as_of") }}', '')::date,
    (select max(snapshot_date) from {{ ref('stg_gh_repos') }})
)
{%- endmacro %}
