# Workflows

Layers 2 and 8 run here. `refresh.yml` and `ci.yml` exist; the rest are added in the stage that needs them. `refresh.yml` needs the repository secrets `GH_API_TOKEN`, `HF_TOKEN` and `HF_DATASET_REPO`. The built-in `GITHUB_TOKEN` is not used because it allows only 1,000 API calls an hour.

| Workflow | Runs | Stage |
| --- | --- | --- |
| `daily.yml` | dbt, publish (GH Archive is not used for current activity) | 2 |
| `ci.yml` | Lint and Python tests on every change (dbt tests added in Stage 2) | 1 |
| `refresh.yml` | Events API every 30 minutes, with retries | 1 (alerts added in 3) |
| `weekly.yml` | deps.dev, OSV and PyPI metadata | 4 |
