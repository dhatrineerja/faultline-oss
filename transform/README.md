# Layer 4: Transform and quality

dbt on DuckDB: `staging`, then `intermediate`, then `marts` (daily metrics, health scores, graph edges). Tests run on every run, and each score row carries its formula version.

**Built in:** Stage 2.

**Done when:** tests cover keys, nulls, ranges and freshness, and a failing test blocks publish.
