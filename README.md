# Faultline

> Stars measure popularity, not health. Faultline measures health from activity, follows it down the dependency tree, and shows that the score actually predicts abandonment.

**Status:** scaffold only. No pipeline, data or scores exist yet. The next step is [Stage 0](#roadmap).

## The problem

Teams choose and keep open-source dependencies using popularity signals (stars, downloads) that say nothing about whether anyone still maintains them. Existing health tools score one repository at a time, so risk that lives further down the dependency chain, or with one overstretched maintainer, stays invisible until something breaks.

The xz backdoor, Log4Shell and left-pad were all dependency-chain or maintainer-concentration problems, which is exactly what per-repository scores miss.

## The pitch

Faultline scores the health of PyPI packages from real activity, finds the risk hidden deep in their dependency trees, and recommends what to use with a plain-language reason. It proves the score works with a published backtest against simple baselines.

| Question | Analysis type | What answers it |
| --- | --- | --- |
| Is this package healthy, and which way is it trending? | Descriptive and diagnostic | Health metrics, cohorts, funnels, trends, anomaly flags |
| Where does risk hide in what I already depend on? | Network analysis | Knowledge graph: transitive risk, maintainer concentration, blast radius, licence conflicts |
| What should I use for this need? | Prescriptive | Search, filter, weighted rank, explanation |
| Does the score predict anything real? | Validation | Backtest against stars, last-commit recency and OpenSSF Scorecard |

**v1 scope:** about 2,000 PyPI packages with a GitHub repository, package-level dependencies, public data only, refreshed about every 30 minutes, at $0 on free tiers.

**Out of scope for v1:** other ecosystems, private repositories, real-time streaming, acting as a vulnerability scanner, and per-person scores of maintainers.

The full reasoning is in [PLAN.md](PLAN.md).

## How it fits together

Scheduled jobs build one source of truth (the Parquet lake), copy what each live feature needs into a store suited to it, and visitors only ever read those copies.

```text
GH Archive, Events API, GitHub API, PyPI, deps.dev, OSV     (1 sources)
        |  GitHub Actions: every 30 min / daily / weekly    (2 ingestion)
        v
Date- and hour-partitioned Parquet on Hugging Face          (3 lake, source of truth)
        |  dbt on DuckDB: staging > intermediate > marts    (4 transform and quality)
        |  NetworkX: PageRank, transitive risk              (5 graph compute)
        v
Neo4j (paths)     Neon + pgvector (search, copied scores)   (6 serving stores)
        |
        v
FastAPI recommendations     Evidence static dashboard       (7 live services)

Alerts, secrets, CI, runbook                                (8 operations)
```

## Repository layout

Each layer folder has a README with its job, the stage that builds it, and its "done when" test.

| Layer | Folder | Built in stage |
| --- | --- | --- |
| 1 Sources | [src/faultline/sources/](src/faultline/sources/) | 1, 3, 4 |
| 2 Ingestion | [src/faultline/ingestion/](src/faultline/ingestion/), [.github/workflows/](.github/workflows/) | 1, 3, 4 |
| 3 Lake | [src/faultline/lake/](src/faultline/lake/) | 1 |
| 4 Transform and quality | [transform/](transform/) (dbt project) | 2 |
| 5 Graph compute | [src/faultline/graph_compute/](src/faultline/graph_compute/) | 4 |
| 6 Serving stores | [src/faultline/serving/](src/faultline/serving/) | 4, 5 |
| 7 Live services | [src/faultline/api/](src/faultline/api/), [dashboard/](dashboard/) | 3, 5 |
| 8 Operations | [ops/](ops/), [.github/workflows/](.github/workflows/) | 3 |
| Evaluation | [src/faultline/evaluation/](src/faultline/evaluation/) | 6 |

Other folders: [config/](config/) holds the tracked package list, repo overrides and versioned score formulas; [docs/](docs/) holds the definitions, limits check and pitch report; `tests/` holds the Python tests; `data/` is local-only and gitignored.

## Roadmap

Do not start a stage until the previous gate passes. Full criteria are in the [plan](PLAN.md#11-roadmap).

| Stage | Build | Est. weeks |
| --- | --- | --- |
| 0 | Setup and definitions | 1 |
| 1 | Daily pipeline | 1 to 2 |
| 2 | Models and score v1 | 1 to 2 |
| 3 | Dashboard, live refresh, alerts (MVP) | 1 |
| 4 | Knowledge graph (required) | 2 |
| 5 | Search and recommendation | 2 |
| 6 | Backfill and backtest | 2 |
| 7 | Launch and write-up | 1 |

## Local setup

Requires Python 3.11+. Dependencies are grouped by layer in `pyproject.toml`, so install only what the current stage needs.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/activate
```

```bash
pip install -e ".[dev]"
```

```bash
cp .env.example .env
```

```bash
pytest
```

## Licence

The code is released under the [Apache License 2.0](LICENSE). The licence for the derived scores will be chosen once the upstream data terms are checked (planned: CC BY 4.0).
