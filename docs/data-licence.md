# Data licence and upstream terms

Decided 2 November 2026. This is a project decision based on the upstream terms read on that date, not legal advice. Re-read the sources before any change to what is published.

## Decision

| What | Licence or rule |
| --- | --- |
| Code | Apache-2.0 (see [LICENSE](../LICENSE)) |
| Published dataset: package-level scores, component values, formula versions, advisory counts | CC BY 4.0, with the attribution notice below |
| Raw lake: GitHub events, pull requests, issues and commits, which contain GitHub usernames | Not published. The Hugging Face dataset that holds it stays private |

GH Archive is not used (see the plan, section 14). Only package-level results are published. Per-person data stays private, which also keeps to the plan's rule against scoring or ranking individual maintainers.

## What each source allows

| Source | Terms found | What it means here |
| --- | --- | --- |
| GitHub API | API terms bar downloading data for spamming or for selling users' personal information. Public repository content may be used by third parties (Terms of Service D.5 and D.8) | Fine to compute and publish package-level metrics. Do not publish usernames or per-person data |
| PyPI | No metadata licence stated. The Terms of Service warn that abusive or excessively frequent API use can lead to suspension and that API tokens may not be shared to get around rate limits | Fine to publish derived facts. Keep requests polite and cache them |
| deps.dev | Generated data is CC BY 4.0. Aggregated data keeps its source's terms. The API is under the Google API Terms of Service, and clients may cache data. No quotas stated | CC BY 4.0 on our derived dataset is compatible. Confirm quotas by email before bulk use (depsdev@google.com) |
| OSV | Each source has its own licence: mostly CC BY 4.0 or CC0, but some sources are CC BY-SA 4.0 or CC BY-NC-ND 4.0 | Only Python-ecosystem advisories (PyPI and GitHub Advisory Database, both CC BY 4.0) are used. Publish counts, not copied advisory text |

## Attribution notice (to appear on the dataset card and the site)

Contains data derived from GitHub, PyPI, deps.dev (CC BY 4.0) and OSV (CC BY 4.0 for the PyPI and GitHub Advisory sources). Package scores by Faultline are licensed CC BY 4.0.

## Still to do before publishing

1. Email deps.dev about bulk use and quotas, as the plan requires before Stage 4 loads.
2. Create a separate public dataset for the derived tables. Do not make the raw lake public.
3. Add this licence and the notice to the dataset card and the README.
