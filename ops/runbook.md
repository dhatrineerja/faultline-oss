# Runbook

Steps for keeping the pipeline running. Run commands from the repository root with the virtual environment active (`.venv\Scripts\Activate.ps1` on Windows). Secrets come from `.env` locally and from repository secrets on GitHub.

## Is the pipeline healthy?

1. Open the repository's Actions tab and look at the newest `refresh` runs. A green tick means the last load worked.
2. For a full report over the week, run `python ops/check_stage1.py`. It lists runs, failures, the longest quiet stretch, rate-limit headroom, repos with gaps and a duplicate check. How to read it is in [docs/stage-1-checkpoint.md](../docs/stage-1-checkpoint.md).
3. Each run also saves a record in the lake under `metrics/events_api/`, with the counts, the rate-limit headroom, and the lists of missing, failed and gapped repos.

## Alerts

- **A failed run:** GitHub emails the account that last edited the workflow. Check Settings, Notifications, Actions on GitHub: email on, "failed workflows only".
- **A run that never happens:** the refresh pings a healthchecks.io check (`HEALTHCHECK_URL` secret) after every good run, and the check alerts by email when no ping arrives within its period plus grace. A failed run also reports itself to the check. Without the secret the ping step is skipped and says so in the log.
- **Setting:** period 3 hours and grace 3 hours, so an alert means about 6 hours without a good run, the same limit the Stage 1 checkpoint uses. Revisit it with the 6-hour rule.

## The outside trigger

GitHub's own 30-minute schedule ran about every 6 hours in the first week (longest gap 10.2 h), and 18 busy repositories lost events between runs because the Events API keeps only the latest 300 per repository. An outside scheduler now starts the `refresh` workflow every 30 minutes; the GitHub schedule stays as a backup. Two refreshes never run at once (the `refresh` concurrency group).

- **Service:** cron-job.org (free), one job, every 30 minutes.
- **Request:** `POST https://api.github.com/repos/dhatrineerja/faultline-oss/actions/workflows/refresh.yml/dispatches` with the headers `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, `Content-Type: application/json` and the body `{"ref":"main"}`. GitHub answers 204 when it starts a run.
- **Token:** a fine-grained GitHub token limited to this one repository, with the permission "Actions: Read and write" and an expiry date. It lives only in the cron-job.org job, never in the repository. When it expires the trigger fails with 401; the GitHub schedule and the heartbeat alert still work, so renew it and nothing is lost for long.
- **Measure it:** `python ops/refresh_gaps.py --since <UTC start>` prints the gaps between successful runs and what started each run. The target is a gap of about 30 minutes.
- **After a few good days:** tighten the heartbeat check (period and grace) from 3 hours each to about 1 hour each.

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

## Incremental repo refresh

`python -m faultline.ingestion.repo_refresh [--no-upload] [--batch N] [--until-done]` runs after every events load (a non-fatal step in `refresh.yml`, 60 repos per run; a failure shows as a warning annotation and the repos stay waiting). It downloads the event days since its watermark, adds repos with new pull request, review, issue, comment, push or release events to a waiting list (earliest unread event time per repo), reads the oldest-waiting repos through GraphQL (only items updated since the repo was last read) and writes them to `refresh/<table>/`. `refresh_reach/part.parquet` records the time before which every changed repo is read; dbt turns it into `as_of`. State is `state/refresh.json`. Cost is about 10 GraphQL points and 9 seconds per repo. The first catch-up (1,163 repos, run locally with `--until-done`, which pauses when fewer than 1,500 points are left) took about 10 hours of mostly waiting for the rate limit and left 2,254 points of headroom at its tightest. If `as_of` stops advancing, look at `repos_waiting` and `reached_at` in the newest `metrics/repo_refresh` record. A repo in `cut_short_repos` hit a page cap during a refresh. To redo from scratch, delete `state/refresh.json`, `refresh/` and `refresh_reach/` from the dataset; the first run then reaches back to 31 October. The earlier `merged_prs/` table and `state/topup.json` in the dataset belong to a replaced job and can be deleted.

## Repos cut short by the page cap

After a backfill, `python -m faultline.ingestion.backfill --deepen --upload` fetches again, with a much higher page cap, every repo that hit the normal cap, and swaps its rows into the existing files. Progress is saved in `state/backfill_deep.json`, so it can be stopped and restarted; it pauses itself when fewer than 1,500 GraphQL points are left. The first run (38 repos) took about 6 hours and cost roughly 3,000 points.

## Refreshing PyPI history

`python -m faultline.ingestion.pypi_metadata` reloads every tracked package's releases and Inactive flag in about 35 seconds and replaces that day's snapshot. Run it before computing scores if the last snapshot is older than a week.

## Computing the scores

From `transform/`: `dbt seed`, `dbt run`, `dbt test`, each with `--profiles-dir .`. The lake is read from `../data/lake`, or from the folder in `DBT_LAKE_DIR`. A test warning on score coverage means fewer than 95% of mapped packages have a score.

## Packages that cannot be loaded

Packages whose GitHub repo answers 404 are listed in `config/unmapped.csv` with the reason. They stay in the tracked set and show as `unmapped`. To fix one, add a row to `config/repo_overrides.csv` with the correct repo.
