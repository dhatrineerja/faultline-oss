# Runbook

Steps for keeping the pipeline running. Run commands from the repository root with the virtual environment active (`.venv\Scripts\Activate.ps1` on Windows). Secrets come from `.env` locally and from repository secrets on GitHub.

## Is the pipeline healthy?

1. Open the repository's Actions tab and look at the newest `refresh` runs. A green tick means the last load worked.
2. For a full report over the week, run `python ops/check_stage1.py`. It lists runs, failures, the longest quiet stretch, rate-limit headroom, repos with gaps and a duplicate check. How to read it is in [docs/stage-1-checkpoint.md](../docs/stage-1-checkpoint.md).
3. Each run also saves a record in the lake under `metrics/events_api/`, with the counts, the rate-limit headroom, and the lists of missing, failed and gapped repos.

## Re-running a failed refresh

The refresh is safe to repeat. Events are merged into hourly partitions by event id, and the per-repo state is saved only after the data is stored, so a failed run changes nothing and the next run picks up where it left off.

1. Actions tab, workflow `refresh`, "Run workflow".
2. If it fails again, open the failed run. The three check steps name the secret at fault (`GH_API_TOKEN`, `HF_TOKEN`, `HF_DATASET_REPO`). Re-enter that secret. Values are trimmed automatically, but an empty or wrong value fails.
3. To run it by hand: `python -m faultline.ingestion.events_api` (add `--no-upload` for a local test).

## After a long outage

The Events API keeps at most 300 events or 90 days per repo. A busy repo can pass 300 events in a few days, so after an outage longer than about a day, some events are gone for good. The job records these as `gap_repos` in the run record.

To fill the window, repeat the 6-month backfill:

1. Delete `data/state/backfill.json` locally and `state/backfill.json` in the Hugging Face dataset.
2. Run `python -m faultline.ingestion.backfill --upload` once an hour until it prints "all shards done". The GraphQL allowance is 5,000 points an hour and the full run needs about 11,000.
3. Re-run `dbt run` and `dbt test` in `transform/`.

## Repos cut short by the page cap

After a backfill, `python -m faultline.ingestion.backfill --deepen --upload` fetches again, with a much higher page cap, every repo that hit the normal cap, and swaps its rows into the existing files. Progress is saved in `state/backfill_deep.json`, so it can be stopped and restarted; it pauses itself when fewer than 1,500 GraphQL points are left. The first run (38 repos) took about 6 hours and cost roughly 3,000 points.

## Refreshing PyPI history

`python -m faultline.ingestion.pypi_metadata` reloads every tracked package's releases and Inactive flag in about 35 seconds and replaces that day's snapshot. Run it before computing scores if the last snapshot is older than a week.

## Computing the scores

From `transform/`: `dbt seed`, `dbt run`, `dbt test`, each with `--profiles-dir .`. The lake is read from `../data/lake`, or from the folder in `DBT_LAKE_DIR`. A test warning on score coverage means fewer than 95% of mapped packages have a score.

## Packages that cannot be loaded

Packages whose GitHub repo answers 404 are listed in `config/unmapped.csv` with the reason. They stay in the tracked set and show as `unmapped`. To fix one, add a row to `config/repo_overrides.csv` with the correct repo.
