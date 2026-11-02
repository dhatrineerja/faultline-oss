{#- Percentile 0 to 100 of a value among the rows that have one. Rows with no value stay null and
    do not distort the ranks. lower_is_better flips the direction, so fewer hours or days
    score higher (definitions.md). -#}
{% macro pct(value, lower_is_better=false) -%}
case
    when {{ value }} is null then null
    else percent_rank() over (
        partition by ({{ value }} is null)
        order by {{ value }} {{ 'desc' if lower_is_better else 'asc' }}
    ) * 100
end
{%- endmacro %}
