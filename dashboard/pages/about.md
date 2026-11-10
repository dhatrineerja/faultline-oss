---
title: How the score works
---

# How the score works

Formula version **v1**. The rules were written down before any data was looked at and are kept in the project repository: `docs/definitions.md` and `config/score_v1.toml`.

## Measures

Each measure is turned into a 0 to 100 position among the tracked packages, then combined with fixed weights. Graph measures (dependency risk, open vulnerabilities) are not in v1, so the other weights are scaled to add up to 100.

| Measure | Weight | What it counts |
| --- | --- | --- |
| Maintainer activity | 20% | Distinct people who merged a pull request or published a release in 90 days |
| Contributor retention | 15% | Share of the earlier 90 days' contributors active again |
| Responsiveness | 15% | Median hours to a first maintainer reply on issues and pull requests |
| Pull request flow | 10% | Share of pull requests merged or closed within 30 days |
| Release recency | 10% | Days since the last PyPI release |
| Maintainer concentration | 10% | Fewest people behind half of the commits in about 6 months |

## Statuses

- **Scored**: enough data. Confidence is "normal" with four or more measures, "low" with two or three.
- **Dormant**: no merge or release by a person in the last 90 days. Scored from what exists; silence is the finding. A finished, stable package can look dormant.
- **Not matched**: no GitHub repository could be loaded.

## Limits

- Scores support decisions. They do not replace a security review, and they are not a prediction for any one package.
- Maintainer concentration describes a package, never a ranking of people. No individual is named.
- Small projects with few pull requests are scored on fewer measures and swing more.

## Data credits

Contains data derived from GitHub, PyPI, deps.dev (CC BY 4.0) and OSV (CC BY 4.0 for the PyPI and GitHub Advisory sources). Package scores by Faultline are licensed CC BY 4.0. The download counts that pick the tracked packages come from the hugovk top-pypi-packages list (ClickHouse PyPI download counts). Dependency and advisory data arrive in a later version; v1 does not use them yet.
