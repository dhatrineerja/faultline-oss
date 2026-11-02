-- A pull request number appears once per repo; a repeat means a snapshot was loaded twice.
select repo, number, count(*) as n
from {{ ref('stg_gh_prs') }}
group by repo, number
having count(*) > 1
