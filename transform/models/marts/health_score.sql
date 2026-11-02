-- Health score v1, one row per tracked package. Each component is turned into a 0 to 100
-- percentile within the tracked set (repo-level components are ranked across repos, so a
-- monorepo's many packages do not count many times), then combined by weight. The graph terms
-- (dependency risk, open vulnerabilities) arrive in Stage 4; until then the weights of the
-- components that exist are rescaled to add up to 100, and graph_terms_included says so.
{% set w = var('weights') %}

with repo_values as (
    select
        r.repo,
        r.is_archived,
        ma.value as maintainer_activity,
        cr.value as contributor_retention,
        rs.value as responsiveness_hours,
        pf.value as pr_flow,
        bf.value as bus_factor
    from {{ ref('stg_gh_repos') }} as r
    left join {{ ref('int_maintainer_activity') }} as ma on ma.repo = r.repo
    left join {{ ref('int_contributor_retention') }} as cr on cr.repo = r.repo
    left join {{ ref('int_responsiveness') }} as rs on rs.repo = r.repo
    left join {{ ref('int_pr_flow') }} as pf on pf.repo = r.repo
    left join {{ ref('int_bus_factor') }} as bf on bf.repo = r.repo
),

repo_pct as (
    select
        *,
        {{ pct('maintainer_activity') }} as pct_maintainer_activity,
        {{ pct('contributor_retention') }} as pct_contributor_retention,
        {{ pct('responsiveness_hours', lower_is_better=true) }} as pct_responsiveness,
        {{ pct('pr_flow') }} as pct_pr_flow,
        {{ pct('bus_factor') }} as pct_bus_factor
    from repo_values
),

package_values as (
    select
        k.package,
        k.repo,
        g.repo is not null as repo_found,
        coalesce(g.is_archived, false) as is_archived,
        coalesce(rr.inactive, false) as is_inactive,
        g.maintainer_activity,
        g.contributor_retention,
        g.responsiveness_hours,
        g.pr_flow,
        rr.value as release_recency_days,
        g.bus_factor,
        g.pct_maintainer_activity,
        g.pct_contributor_retention,
        g.pct_responsiveness,
        g.pct_pr_flow,
        g.pct_bus_factor
    from {{ ref('stg_packages') }} as k
    left join repo_pct as g on g.repo = k.repo
    left join {{ ref('int_release_recency') }} as rr on rr.package = k.package
),

package_pct as (
    select
        *,
        {{ pct('release_recency_days', lower_is_better=true) }} as pct_release_recency
    from package_values
),

scored as (
    select
        *,
        (pct_maintainer_activity is not null)::int + (pct_contributor_retention is not null)::int
            + (pct_responsiveness is not null)::int + (pct_pr_flow is not null)::int
            + (pct_release_recency is not null)::int + (pct_bus_factor is not null)::int
            as n_components,
        coalesce(pct_maintainer_activity, 0) * {{ w['maintainer_activity'] }}
            + coalesce(pct_contributor_retention, 0) * {{ w['contributor_retention'] }}
            + coalesce(pct_responsiveness, 0) * {{ w['responsiveness'] }}
            + coalesce(pct_pr_flow, 0) * {{ w['pr_flow'] }}
            + coalesce(pct_release_recency, 0) * {{ w['release_recency'] }}
            + coalesce(pct_bus_factor, 0) * {{ w['bus_factor'] }} as weighted_sum,
        (pct_maintainer_activity is not null)::int * {{ w['maintainer_activity'] }}
            + (pct_contributor_retention is not null)::int * {{ w['contributor_retention'] }}
            + (pct_responsiveness is not null)::int * {{ w['responsiveness'] }}
            + (pct_pr_flow is not null)::int * {{ w['pr_flow'] }}
            + (pct_release_recency is not null)::int * {{ w['release_recency'] }}
            + (pct_bus_factor is not null)::int * {{ w['bus_factor'] }} as weight_used
    from package_pct
)

select
    package,
    repo,
    (select as_of from {{ ref('int_params') }}) as as_of,
    '{{ var("score_formula_version") }}' as formula_version,
    case
        when not repo_found then 'unmapped'
        when n_components >= {{ var('insufficient_data_below') }} then 'scored'
        -- no human merged or released in the window: the silence is the finding, so the package
        -- is scored on the components that exist instead of being hidden as missing data
        when maintainer_activity = 0 and release_recency_days is not null then 'dormant'
        else 'insufficient_data'
    end as status,
    case
        when repo_found
         and (n_components >= {{ var('insufficient_data_below') }}
              or (maintainer_activity = 0 and release_recency_days is not null))
            then round(weighted_sum / weight_used, 1)
    end as score,
    n_components,
    false as graph_terms_included,
    is_archived,
    is_inactive,
    maintainer_activity,
    contributor_retention,
    responsiveness_hours,
    pr_flow,
    release_recency_days,
    bus_factor,
    pct_maintainer_activity,
    pct_contributor_retention,
    pct_responsiveness,
    pct_pr_flow,
    pct_release_recency,
    pct_bus_factor
from scored
