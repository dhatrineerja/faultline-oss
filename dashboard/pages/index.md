---
title: Faultline
---

# Faultline: package health for 2,000 PyPI packages

Scores show which widely used Python packages have **low recent activity** or may **need support**, based on public GitHub and PyPI data. A score supports a decision; it does not replace a security review.

```sql meta
select * from faultline.meta
```

<BigValue data={meta} value=built_at title="Site built" />
<BigValue data={meta} value=as_of title="Scores as of (day)" />
<BigValue data={meta} value=formula_version title="Formula version" />
<BigValue data={meta} value=repos_waiting title="Repos waiting for a refresh read" />

Scores cover the 90 days up to the end of the "as of" day. The site is rebuilt after each good data refresh; if a run fails, the last good data stays up.

```sql by_status
select
  case status
    when 'scored' then 'Scored'
    when 'dormant' then 'Dormant: no recent merge or release'
    when 'unmapped' then 'Not matched to a GitHub repo'
    else 'Insufficient data'
  end as status,
  count(*) as packages
from faultline.scores
group by 1
order by 2 desc
```

<DataTable data={by_status} />

## Lowest scores that need a closer look

Archived or deprecated packages are shown with their flags. Low-confidence scores rest on only two measures.

```sql watch
select
  package,
  '/packages/' || package as link,
  status,
  confidence,
  score,
  release_recency_days as days_since_release,
  is_archived,
  is_inactive
from faultline.scores
where score is not null
order by score asc
limit 25
```

<DataTable data={watch} link=link rows=25>
  <Column id=package />
  <Column id=score />
  <Column id=status />
  <Column id=confidence />
  <Column id=days_since_release />
  <Column id=is_archived />
  <Column id=is_inactive />
</DataTable>

## All packages

```sql all_packages
select
  package,
  '/packages/' || package as link,
  status,
  confidence,
  score,
  release_recency_days as days_since_release,
  repo
from faultline.scores
order by package
```

<DataTable data={all_packages} link=link search=true rows=20>
  <Column id=package />
  <Column id=score />
  <Column id=status />
  <Column id=confidence />
  <Column id=days_since_release />
  <Column id=repo />
</DataTable>

See [how the score works](/about) and the data credits.
