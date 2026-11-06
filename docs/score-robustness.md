# Score robustness check (2026-11-06)

A check, run before Stage 3, of whether the v1 score depends on choices that were made after seeing data. It is not a validation: nothing here says the score predicts abandonment. That is the Stage 6 backtest.

## What was and was not fitted

- **Weights:** unchanged since the first commit on 2026-11-01, before any data was loaded (`git log -- config/score_v1.toml` shows one commit).
- **Outcome labels:** not used anywhere in the score. No part of the score has been tuned against "abandoned".
- **Minimum samples** (PRs 5, responsiveness items 5, earlier contributors 3, commits 10): first appear in the Stage 2 commit with the models. The definitions say they were set before the first run, but git cannot prove the order.
- **Decided after seeing data:** the dormant status (after 448 inactive packages showed as missing), the two-component rule (after 178 quiet projects were unscored), and the deeper backfill for capped repos (completeness, not scoring). Each is in the changelog in [definitions.md](definitions.md).

## Sensitivity (1,996 mapped packages)

| Change | Rank correlation with the current score | Overlap of the bottom 5% |
| --- | --- | --- |
| Each weight randomly changed by up to 30% (200 draws) | at least 0.994 | at least 0.96 |
| All weights equal | 0.993 | 0.98 |
| Minimum samples looser (3 / 3 / 2 / 5) | 0.985 | 0.96 |
| Minimum samples stricter (8 / 8 / 5 / 20) | 0.985 | 0.96 |
| Looser against stricter | 0.975 | 0.94 |
| Without contributor retention / responsiveness / PR flow / release recency / bus factor | 0.976 to 0.993 | 0.96 to 1.00 |
| Without maintainer activity | 0.907 | 0.80 |

A control run with nothing changed reproduced the baseline on all 1,996 rows.

## What this means

- The ranking is stable under reasonable changes to weights and thresholds. That is good for generalising, but it also means the weights barely matter, and tuning them in the backtest is unlikely to change much.
- Maintainer activity carries the score. Dropping it is the only change that moves the bottom 5% noticeably.
- **The bottom 5% (99 packages) is almost entirely dormant: 93 dormant, 97 low confidence, 2 normal.** That list is what the backtest will use as its warning line. If it is mostly "no human merge or release in 90 days", it may do little more than last-commit recency, one of the baselines. This is the main risk for Stage 6 and should be checked first.
- Percentiles are ranked within the tracked set, so a score is relative to these 2,000 packages.

## Is the bottom 5% just a recency list? (checked 2026-11-06)

The bottom 5% is 99 packages. It was compared with the 99 worst packages under four single measures, using the 49 packages that are archived or marked Inactive as a rough stand-in for "abandoned". That stand-in describes today, not the future, and it favours recency measures: an archived repo has stopped committing by definition. So this shows how the lists differ, not whether the score predicts. Ties were broken at random, 200 times; the score's own count moves by one between runs.

The last-commit row uses each repo's real last commit date, fetched once for all repos (`repo_meta` job). An earlier version of this table used only the six-month backfill, where 388 repos had no commit and tied; it wrongly made the score look better than last commit.

| Warning list (99 packages) | Overlap with the score's list | Archived or Inactive caught (of 49) |
| --- | --- | --- |
| Score, bottom 5% | 1.00 | 15 |
| Oldest last commit (full history) | 0.57 | 19 |
| Oldest PyPI release | 0.75 | 11 |
| Fewest stars | 0.06 | 2 |
| Fewest people who merged or released in 90 days | 0.09 | 8 |

- **On this stand-in the score does not beat last commit alone** (15 against 19). This is the result to take seriously. It may be an artefact of the stand-in, but nothing here shows the score adding value over a simple recency measure.
- The score's list overlaps 57% with the oldest last commits and 75% with the oldest releases. It is largely a recency list, as feared.
- Stars alone are nearly useless here (2 of 49), which supports using stars only as a weak baseline.
- The real test is Stage 6: outcomes after each cutoff, with every baseline built only from data before that cutoff. If the score cannot beat last commit there, the report must say so.

What this changes for Stage 6: "oldest release alone" is added as a baseline next to stars, last commit and Scorecard, and the report must show what the score adds over each. The last-commit baseline uses full history.
