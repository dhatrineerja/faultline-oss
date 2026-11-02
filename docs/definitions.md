# Definitions

**Status: decided and committed.** This is the main Stage 0 deliverable. The plan requires these to be committed before any data is looked at, so the git history proves they were not fitted to results. Change them afterwards only with a new formula version and a note in the changelog below.

Values come from [PLAN.md](../PLAN.md). Decisions made on 2026-11-01 are filled in below.

## Abandoned

The backtest's outcome label. A package counts as abandoned if any of these holds:

- Its GitHub repository is archived.
- It is marked deprecated: its PyPI classifiers include `Development Status :: 7 - Inactive`. README notices and yanked releases are not used, because they are noisy or hard to rebuild at a past date.
- It has no release and no commit for 12 months. Commits by bots (for example dependabot, renovate, github-actions) do not count; the bot-name list is kept in the repository and versioned with the formula.

A mature, deliberately finished package is not excluded. It is accepted as a known false alarm, and the backtest reports the false-alarm rate.

## Tracked package set

About 2,000 PyPI packages that have a GitHub repository.

Selection rule: at each date, rank PyPI packages that have a GitHub repository by downloads in the prior 30 days and take the top 2,000. The first list is built on 2026-11-01 from the hugovk top-pypi-packages ranking (ClickHouse PyPI download counts). The backtest rebuilds the list this way at every cutoff, using only data from before that cutoff.

## Score components (formula v1)

Weights live in [config/score_v1.toml](../config/score_v1.toml). Windows are 90 days unless stated. Each component becomes a 0 to 100 percentile within the tracked set.

| Component | Definition | Weight | Decision |
| --- | --- | --- | --- |
| Maintainer activity | Distinct people who merged, released or triaged | 20% | Triage = labelling, assigning or closing an issue or pull request. Reviews and comments are not triage. |
| Contributor retention | Share of last window's contributors active again this window | 15% | A contribution is a merged pull request or a commit. Issues and comments do not count. |
| Responsiveness | Median hours to first maintainer response on issues and PRs | 15% | A maintainer is an account with GitHub author association OWNER, MEMBER or COLLABORATOR. Bot accounts are excluded. |
| PR flow | Share of PRs merged or closed within 30 days | 10% | |
| Release recency | Days since the last PyPI release | 10% | |
| Bus factor | Fewest people who made 50% of commits in 12 months | 10% | |
| Dependency risk (graph) | Worst health among dependencies, discounted by depth | 15% | |
| Open vulnerabilities | Unfixed OSV advisories affecting the latest release | 5% | |

Dependency risk uses each dependency's own health (the score without its dependency term), which avoids a circular score:

```latex
\text{Health}_v = \sum_i w_i \cdot \text{pct}(x_i), \quad \text{DepRisk}(p) = \max_{d \in \text{deps}(p)} \big(100 - \text{OwnHealth}(d)\big) \cdot 0.6^{\,\text{depth}(d)-1}
```

Percentile direction: for responsiveness hours and release-recency days, lower is better, so fewer hours and fewer days score higher. For the other components, higher is better. Dependency risk and open vulnerabilities enter the score as health (a higher risk lowers it).

Insufficient data: the six non-graph components are maintainer activity, contributor retention, responsiveness, PR flow, release recency and bus factor. If fewer than 3 of them can be computed, the package shows "insufficient data" instead of a score.

## Backtest rules

Set in the plan; repeated here so they are locked with the rest.

- Score only with data from before a cutoff, then check the next 6 to 12 months.
- Use rolling cutoffs (for example every quarter over two years). Tune weights on early cutoffs only and report on later ones.
- Baselines: stars alone, last-commit recency alone, OpenSSF Scorecard.
- Report precision and recall for each, precision at a fixed alert budget (for example the bottom 5% of scores), PR-AUC, lead time, and the score with and without the dependency-risk term.

- Cutoffs: quarterly, nine in all, from 2023-10-01 to 2025-10-01. Each is judged on a 12-month outcome window, which has fully closed for the last cutoff.
- Tuning uses the first five cutoffs (2023-10-01 to 2024-10-01). Reported results use the last four (2025-01-01 to 2025-10-01) and the weights are not changed after that.
- Warning line: the bottom 5% of scores at each cutoff. Every baseline is cut at the same 5%, so the comparison is fair.

## Rules added while building the score (Stage 2)

These fill gaps the data forced. They are all in `transform/dbt_project.yml` and the models, and every one is in the changelog below.

- **Dormant status.** A package with no human merge or release in the current window and a known PyPI release date is scored from the components that exist and marked `dormant`, because silence is the finding. Added after the first run showed that the "fewer than 3 components" rule hid 448 inactive packages as "insufficient data". The rule was chosen on that reasoning, not by tuning to scores.
- **Minimum samples** (set before the first run, not tuned): pull-request flow needs 5 PRs, responsiveness 5 items, contributor retention 3 contributors in the earlier window, bus factor 10 commits.
- **Missing graph terms.** Until Stage 4, dependency risk and open vulnerabilities do not exist. The weights of the components that do exist are rescaled to add up to 100, and `graph_terms_included` is false.
- **Triage is not counted.** The backfill holds no record of who labelled or closed an item, so maintainer activity counts people who merged a pull request or published a release. Revisit when the data allows.
- **Bus factor window.** The backfill holds about 6 months of commits, so bus factor is measured over those, not 12 months.
- **Responsiveness uses the first three comments and reviews.** An item whose first maintainer reply came later is left out, so the measure is slightly optimistic.
- **Capped repositories.** If a repo hit a page cap in the backfill, a window older than the oldest item fetched is not measured for that repo, and the component is left empty.
- **Bots.** Excluded using `transform/seeds/bots.csv` plus names ending in `[bot]` or `-bot`, because GraphQL returns bot logins without the `[bot]` suffix.
- **Ranking.** Repo-level components are ranked across repositories, so a monorepo's many packages do not count many times. Release recency is ranked across packages.
- **Windows.** The score is computed as of the newest backfill snapshot date. The current window is the 90 days up to the end of that day.

## Language

Maintainer concentration is a property of a package, never a ranking of people. Say "needs support" or "low recent activity" on anything public.

## Changelog

| Date | Formula version | Change |
| --- | --- | --- |
| 2026-11-01 | v1 | Initial definitions; all open items decided |
| 2026-11-01 | v1 | Tracked set ranked by 30-day downloads instead of 90-day, because only a 30-day ranking is freely available. Changed before any data was examined. |
| 2026-11-02 | v1 | Stage 2 rules added: minimum samples, graph-term rescaling, triage not counted, 6-month bus factor, first-three-replies responsiveness, cap handling, bot list, ranking and window rules. Decided before the first score run. |
| 2026-11-02 | v1 | Dormant status added after the first run showed 448 inactive packages hidden as insufficient data. Chosen on the principle that silence is a measurement; no weight or threshold was changed. |
