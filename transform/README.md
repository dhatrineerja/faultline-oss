# Layer 4: Transform and quality

dbt on DuckDB: `staging`, then `intermediate`, then `marts` (daily metrics, health scores, graph edges). Tests run on every run, and each score row carries its formula version.

**Built in:** Stage 2. Run from this folder: `dbt seed`, `dbt run`, `dbt test` with `--profiles-dir .`. The models read the lake from `../data/lake` (or the `DBT_LAKE_DIR` environment variable) and write `../data/faultline.duckdb`.

| Layer | Models |
| --- | --- |
| staging | `stg_packages`, `stg_gh_repos`, `stg_gh_prs`, `stg_gh_issues`, `stg_gh_commits`, `stg_gh_releases`, `stg_pypi_packages`, `stg_pypi_releases` (newest snapshot only; the GitHub ones also merge in the refresh rows by key) |
| intermediate | `int_params` (windows), `int_coverage`, `int_people_events`, and one model per component: `int_maintainer_activity`, `int_contributor_retention`, `int_responsiveness`, `int_pr_flow`, `int_bus_factor`, `int_release_recency` |
| marts | `health_score`, one row per tracked package, with status `scored`, `dormant`, `insufficient_data` or `unmapped`, and a `confidence` of `normal` (four or more components) or `low` |

CI runs `dbt parse` only (no lake there); run `dbt test` here before changing a model. Weights and thresholds are in `dbt_project.yml`; a Python test checks they equal `config/score_v1.toml`. The rules behind each component are in [docs/definitions.md](../docs/definitions.md).

**Done when:** tests cover keys, nulls, ranges and freshness, and a failing test blocks publish.
