# Config

Committed, non-secret settings. Secrets belong in `.env` locally and platform secret settings in production.

| File | Purpose |
| --- | --- |
| `packages.csv` | The tracked package set (about 2,000), filled in Stage 0 |
| `unmapped.csv` | Tracked packages whose GitHub repo cannot be read, with the reason. They stay in `packages.csv` and are reported as unmapped, never dropped silently |
| `repo_overrides.csv` | Manual PyPI-to-GitHub fixes for packages the automatic mapping misses or gets wrong |
| `score_v1.toml` | Health score formula v1; each new formula gets a new file |
