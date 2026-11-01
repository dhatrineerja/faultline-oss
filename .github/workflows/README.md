# Workflows

Layers 2 and 8 run here. No workflows are active yet, and each one gets added in the stage that needs it.

| Workflow | Runs | Stage |
| --- | --- | --- |
| `daily.yml` | GH Archive load, dbt, publish | 1 |
| `ci.yml` | Python tests and dbt tests on every change | 2 |
| `refresh.yml` | Events API every 30 minutes | 3 |
| `weekly.yml` | deps.dev, OSV and PyPI metadata | 4 |
