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

The bottom 5% is 99 packages. It was compared with the 99 worst packages under three single measures, using the 49 packages that are archived or marked Inactive as a rough stand-in for "abandoned". That stand-in describes today, not the future, and an archived repo scores low almost by definition, so it only shows how the lists differ, not whether the score predicts. Ties were broken at random, 200 times.

| Warning list (99 packages) | Overlap with the score's list | Archived or Inactive caught (of 49) |
| --- | --- | --- |
| Score, bottom 5% | 1.00 | 16 |
| Oldest PyPI release | 0.75 | 11 |
| Oldest last commit | 0.14 | 9 |
| Fewest people who merged or released in 90 days | 0.09 | 8 |

- The score's list is mostly the packages with the oldest PyPI release: 75% overlap, and the median release age is 2,192 days (about six years) against 517 for other dormant packages. So the worry is partly right: the list leans heavily on release age.
- It is not only release age. A quarter of the list differs, and it caught 16 of the 49 against 11 for release age alone. These are small numbers on a weak stand-in, so this is a hint, not a result.
- The last-commit baseline is weak here by construction: the backfill holds six months of commits, and 388 repos have none in that window, so many are tied. A fair version needs each repo's real last commit date, which is one cheap call per repo.

What this changes for Stage 6: "oldest release alone" is added as a baseline next to stars, last commit and Scorecard, and the report must show what the score adds over it. The last-commit baseline must use full history.
