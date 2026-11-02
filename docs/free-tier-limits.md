# Free-tier limits check

The Stage 0 gate needs every limit confirmed in each provider's own dashboard or pricing page. The "Plan figure" column is what the plan assumed. On 2 November 2026 the owner confirmed in each provider's dashboard that the services are free to use, without recording the exact figures. Add the figures and dates below when convenient. Measured so far: the GitHub REST allowance is 5,000 calls an hour and GraphQL 5,000 points an hour (observed in API responses), and the lake is about 101 MB in the Hugging Face dataset.

| Service | Plan figure | Confirmed figure | Checked on |
| --- | --- | --- | --- |
| GitHub API | 5,000 calls an hour with a personal token | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| GitHub Actions | Schedules can start late; can be switched off after long repo inactivity | Free tier confirmed by owner; figure not recorded. Observed: 4 scheduled runs in the first 15 hours against about 30 expected | 2026-11-02 |
| Hugging Face dataset | Check dataset size guidance | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| Hugging Face Spaces | 2 vCPU, 16 GB; sleeps after 48 h idle; disk not persistent | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| Neo4j AuraDB Free | 50,000 nodes, 175,000 relationships; pauses after 3 idle days | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| Neon Postgres | About 500 MB storage (unconfirmed in the plan) | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| Vercel | Rebuild after each refresh | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
| deps.dev | No quotas stated in the docs; keep requests gentle | Free tier confirmed by owner; figure not recorded | 2026-11-02 |
