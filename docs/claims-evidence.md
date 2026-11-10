# Claims and the evidence for them

Each public claim about the pipeline, the exact test that decides it, and the measurements taken. The checks are run by [ops/verify_claims.py](../ops/verify_claims.py) from live data (GitHub's run history, the saved run records in the private dataset, and CI), so a result can be repeated by anyone with the tokens:

```text
python ops/verify_claims.py --since 2026-11-09T19:10 --out docs/claims-evidence.md.latest
```

A claim is marked PASS only when the measured number meets the stated limit. PENDING means the time has not passed yet, not that it failed.

| Claim | Pass rule |
| --- | --- |
| C1 Events load about every 30 minutes | Longest gap between successful runs, and the time since the last one, both under 45 minutes |
| C2 No stretch over 6 hours without a good run, for 7 straight days | 7 days measured, longest gap 6 hours or less |
| C3 Scores follow the live data | The refresh has reached to within 60 minutes of now |
| C4 Stays inside the free GraphQL allowance | Lowest headroom at least 1,500 points; no repo cut short |
| C5 The newest commit passes CI | CI run for the head commit succeeded |

The 30-minute figure in the plan is "about": the outside trigger starts a run every 30 minutes and a run takes 1 to 2 minutes, so 45 minutes is the limit that still counts.

## Measurement 1: 2026-11-10 07:16 UTC (commit 240422a)

Measured 2026-11-10 07:17 UTC; trigger window starts 2026-11-09 19:10 UTC.

| Claim | What it says | Result | Evidence |
| --- | --- | --- | --- |
| C1 | Events load about every 30 min | **PASS** | 27 of 27 runs succeeded over 12.1 h; median gap 0.50 h, longest 0.51 h, time since last success 0.27 h (limit 0.75 h) |
| C2 | No gap over 6 h for 7 straight days | **PENDING** | 0.50 of 7 days measured; longest gap so far 0.51 h; earliest pass 2026-11-16 19:10 UTC |
| C3 | Scores within 60 min of live data | **FAIL** | refresh reached 2026-11-09 20:46 UTC, 631 min before now; 320 repos waiting |
| C4 | Stays inside the free GraphQL allowance | **PASS** | lowest headroom 2254 points over 15 refresh runs (floor 1500); cut-short repos in newest run: 0 |
| C5 | Newest commit passes CI | **FAIL** | commit 348e509: None |

How to read it:

- **C3 failed, and the cause is known.** The refresh had 320 repos waiting. A 10-hour pile of events built up between my local catch-up and the first run of the new job, and the job read only 60 repos per run against about 30 new repos arriving per run. Fix: 100 repos per run (commit 348e509), which uses about 2,000 of the 5,000 hourly GraphQL points. The next measurement below shows whether it cleared.
- **C5 shows `None`** because CI for the new commit had not finished at the moment of measurement. The previous commit (240422a) passed.
- **C2 cannot be decided before 16 November 2026.** It needs 7 days of triggered runs; 12 hours have passed with a longest gap of 0.51 hours.

## Test results on 2026-11-10

| Check | Command | Result |
| --- | --- | --- |
| Python tests | `python -m pytest -q` | 17 passed |
| Lint | `ruff check src tests ops` | all checks passed |
| Data tests (dbt) | `dbt test --profiles-dir .` in `transform/` | 32 passed, 0 warnings, 0 errors |
| CI on the previous commit | `ci` workflow, commit 240422a | success |
| Refresh workflow, new job step | runs 42765696751 and 42769004466 | every step succeeded, including "Refresh changed repos" and the heartbeat ping |

## Still not covered by a test

- **Failure alerts:** the heartbeat's ping is verified, but a deliberately broken run that sends an alert is a Stage 3 item and has not been done.
- **Site keeps the last good data:** there is no site yet.
- **Score freshness over a quiet week:** only measured once the backlog has cleared (C3).

## Measurement 2: 2026-11-10 12:44 UTC (commit 5d3b6fa), after the backlog cleared

The refresh now reads 100 repos per run (commit 348e509). The backlog went 380, 350, 320, 256, 183, 114, 0 over the runs of 10 November, and the scores moved from `as_of` 8 Nov to 9 Nov. Local `dbt run` on the synced lake: 18 models built; `dbt test`: 32 passed, 0 warnings, 0 errors. Statuses: 1,561 scored, 435 dormant, 4 unmapped.

The measurement script was corrected before this run in two ways: a run still in progress counts as started (its first step loads the events), and a CI run not yet finished is PENDING, not FAIL. The rules in the table at the top did not change.

| Claim | What it says | Result | Evidence |
| --- | --- | --- | --- |
| C1 | Events load about every 30 min | **PASS** | 38 of 38 runs succeeded over 17.6 h; median gap 0.50 h, longest 0.51 h, time since the newest run started 0.22 h (limit 0.75 h) |
| C2 | No gap over 6 h for 7 straight days | **PENDING** | 0.73 of 7 days measured; longest gap so far 0.51 h; earliest pass 2026-11-16 19:10 UTC |
| C3 | Scores within 60 min of live data | **PASS** | refresh reached 2026-11-10 12:03 UTC, 40 min before now; 0 repos waiting |
| C4 | Stays inside the free GraphQL allowance | **PASS** | lowest headroom 2254 points over 26 refresh runs (floor 1500); cut-short repos in newest run: 0 |
| C5 | Newest commit passes CI | **PASS** | commit 5d3b6fa: success |

C1, C3, C4 and C5 pass. C2 stays PENDING until 2026-11-16 19:10 UTC; the daily `claims-check` workflow measures it from then on.
