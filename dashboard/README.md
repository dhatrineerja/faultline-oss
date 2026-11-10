# Layer 7: Dashboard

Evidence.dev (open-source v40) static site, built from CSV exports of the derived tables and published to Vercel. Being static, it keeps the last good data if a pipeline run fails.

| Page | Content |
| --- | --- |
| `/` | Build time, scores-as-of day, formula version, refresh backlog, status counts, 25 lowest scores, searchable table of all packages |
| `/packages/<name>` | One page per tracked package: score, status, confidence, the six measures and their 0 to 100 positions |
| `/about` | Weights, statuses, limits, data credits and the CC BY 4.0 attribution notice |

**Build locally** (from the repository root, lake and dbt run first):

```text
python ops/sync_lake.py                    # lake from the private dataset
cd transform; dbt run --profiles-dir .; dbt test --profiles-dir .; cd ..
python ops/export_site_data.py             # writes dashboard/sources/faultline/*.csv (not committed)
cd dashboard; npm ci; npx evidence sources; npx evidence build
```

The exported CSVs hold package-level values only: no usernames and no raw events. `.npmrc` sets `legacy-peer-deps` because Evidence 40 pins older peers than the current TypeScript.

**Publishing:** [.github/workflows/site.yml](../.github/workflows/site.yml) runs after a good refresh (once an hour), runs the dbt tests, and stops before the deploy if any step fails. The Vercel step runs only when the repository variable `PUBLISH_SITE` is `true`. Set it after confirming the data licence in [docs/data-licence.md](../docs/data-licence.md). Secrets: `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_ID` (passed as `VERCEL_ORG_ID`).

**Done when:** it rebuilds after each refresh, loads fast on mobile, and shows the formula version.
