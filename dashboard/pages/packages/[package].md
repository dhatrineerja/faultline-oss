---
title: Package
---

```sql p
select * from faultline.scores where package = '${params.package}'
```

```sql meta
select * from faultline.meta
```

# {params.package}

<BigValue data={p} value=score title="Health score (0 to 100, higher is healthier)" />
<BigValue data={p} value=status title="Status" />
<BigValue data={p} value=confidence title="Confidence" />
<BigValue data={p} value=as_of title="As of (day)" />

Repository: <Value data={p} column=repo />. Formula version <Value data={meta} column=formula_version />.

## What the score is made of

Each measure becomes a 0 to 100 position within the 2,000 tracked packages (100 is best). Empty means there was too little data to measure it.

```sql parts
select 'Maintainer activity (people who merged or released)' as measure, maintainer_activity as value, pct_maintainer_activity as position from p
union all select 'Contributor retention (share of earlier contributors still active)', contributor_retention, pct_contributor_retention from p
union all select 'Responsiveness (median hours to a first maintainer reply)', responsiveness_hours, pct_responsiveness from p
union all select 'Pull request flow (share merged or closed within 30 days)', pr_flow, pct_pr_flow from p
union all select 'Release recency (days since the last PyPI release)', release_recency_days, pct_release_recency from p
union all select 'Maintainer concentration (fewest people behind half of recent commits)', bus_factor, pct_bus_factor from p
```

<DataTable data={parts}>
  <Column id=measure />
  <Column id=value />
  <Column id=position title="Position (0 to 100)" />
</DataTable>

<BarChart data={parts} x=measure y=position swapXY=true yMax=100 />

Flags: archived on GitHub: <Value data={p} column=is_archived />. Marked inactive on PyPI: <Value data={p} column=is_inactive />.

A "dormant" status means no merge or release by a person in the last 90 days. A "low" confidence score rests on two measures only, so treat it as a prompt to look, not a verdict. [How the score works](/about).
