# Stage 1 checkpoint: 7 straight days of runs

This document records how the last Stage 1 checkpoint is measured and what has been found so far. The checkpoint is the one part of Stage 1 that can only be met by waiting.

## What the plan requires

[PLAN.md](../PLAN.md), section 11.1, Stage 1: the first full load completes across the rate limit; the 6-month backfill covers at least 95% of tracked repositories; **7 straight days of runs**; re-running gives identical row counts; unchanged repositories cost no rate limit.

The point of the 7-day run is to show that the 30-minute refresh keeps working on its own, with nobody touching it, and that no data is lost or doubled along the way.

## Which parts are already met

| Checkpoint item | Status | Evidence |
| --- | --- | --- |
| First full load completes across the rate limit | Met | 1,642 of 1,647 repos have saved state; the other five are in [config/unmapped.csv](../config/unmapped.csv) |
| 6-month backfill covers at least 95% of repos | Met | 1,643 of 1,647 repos (99.8%), 33 shards, about 11,000 GraphQL points |
| Re-running gives identical row counts | Met | Unit tests for the partition merge and the shard writer; a re-run of the same repos added no events |
| Unchanged repos cost no rate limit | Met | On a re-run of 60 repos, 55 answered "unchanged" (HTTP 304), which GitHub does not count |
| **7 straight days of runs** | **In progress** | See the log below |

## How "7 straight days" is judged

The script [ops/check_stage1.py](../ops/check_stage1.py) measures the week from the first successful scheduled run after the fix (1 November 2026, 19:50 UTC). It passes only if all of these hold:

| Criterion | Why it matters |
| --- | --- |
| At least 7 days have passed since that run | The checkpoint is about a week of steady running |
| No failed scheduled runs | A failure means something needed fixing |
| No stretch longer than 6 hours without a successful run (a limit chosen for this script, not stated in the plan) | GitHub starts scheduled runs late, but the data must not go stale for long |
| No duplicate event ids in the stored events | Proves the merge never double-counts |
| Saved state covers every loadable repo (1,642 of 1,647) | Proves every repo is being followed |

The report also shows, without a pass or fail: the number of scheduled runs against the 336 a perfect week would have, how often a run stopped early on the rate limit, the lowest rate-limit headroom, how many repos had a **gap** (more new events than one run could fetch, so some events were lost), and events per day.

## How to run it

From the repository root, with the virtual environment active:

```text
python ops/check_stage1.py
```

It reads the run history from GitHub (public), and the saved run records and stored events from the private Hugging Face dataset, using the tokens in `.env`. The first run downloads about 1,500 small files and takes several minutes; later runs reuse a local cache in `data/checkpoint_cache/`. It exits with code 0 only if every criterion passes.

## What to do with the result

- **Everything passes after 19:50 UTC on 8 November 2026 (the automatic check runs on the morning of 9 November):** record the report below as the final entry, mark the table above as met, and close the Stage 1 checkpoint in the plan.
- **Runs were skipped or late but nothing failed:** this is the known GitHub schedule risk (section 13 of the plan). Look at the longest quiet stretch and at the gap count. If gaps exist, follow "After a long outage" in [ops/runbook.md](../ops/runbook.md).
- **A run failed:** open it on the Actions tab, fix the cause, and restart the week from the next successful run, as the plan says "straight".

## Log of measurements

Each entry is the output of the script on that date.

### Measurement 1, day 1: 2026-11-02 11:59 UTC

Window: 2026-11-01 19:50 UTC to now (0 days 16 h).

| Measure | Value |
| --- | --- |
| Scheduled runs completed | 4 (expected about 32 at every 30 minutes) |
| Successful / failed | 4 / 0 |
| Longest stretch without a successful run | 7.6 h |
| Run records saved | 1 |
| Runs that stopped early on the rate limit | 0 |
| Lowest rate-limit headroom seen | 4990 |
| Repos with a gap (more events than one run could fetch) | 0 |
| Stored events / distinct ids | 153732 / 153732 |
| Repos with saved state | 1642 of 1642 loadable |

Events per day (last 7 days): 2026-10-26 7303, 2026-10-27 7765, 2026-10-28 9955, 2026-10-29 12331, 2026-10-30 15168, 2026-10-31 10609, 2026-11-01 17317, 2026-11-02 9455

| Pass criterion | Result |
| --- | --- |
| 7 days elapsed since the first good run | not yet |
| no failed scheduled runs | PASS |
| no stretch over 6 h without a successful run | FAIL |
| no duplicate event ids in the lake | PASS |
| state covers all 1642 loadable repos | PASS |

Run outcomes: {'success': 4}

**Reading of measurement 1.** Four scheduled runs completed in the first 16 hours, against about 32 for a perfect schedule, and none failed. The runs came about every 3 to 7 hours: GitHub starts scheduled workflows late and skips some, which is the known risk in section 13 of the plan, and it is heavier here than expected. Nothing was lost so far: no duplicate events, every loadable repo has state, and no repo had a gap yet. Only one run record exists because run records were added after the first runs. The "no stretch over 6 hours" criterion currently fails (longest 7.6 hours). The 6-hour limit is not in the plan, which asks only for "7 straight days of runs"; it was chosen when the script was written, as a way to catch stale data. It is left as written for now. If the schedule stays this slow, the options are to trigger the job from an outside scheduler or to change the limit, with a note in the plan either way.
