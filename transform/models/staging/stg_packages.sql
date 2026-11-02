-- One row per tracked package and the GitHub repo it maps to (lower-case, the join key).
select
    package,
    lower(github_repo) as repo,
    cast(added_on as date) as added_on,
    selection_reason
from read_csv('{{ var("config_dir") }}/packages.csv', header = true)
