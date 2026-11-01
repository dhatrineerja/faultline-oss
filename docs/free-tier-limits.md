# Free-tier limits check

The Stage 0 gate needs every limit confirmed in each provider's own dashboard or pricing page. The "Plan figure" column is what the plan assumed. Nothing here has been confirmed yet.

| Service | Plan figure | Confirmed figure | Checked on |
| --- | --- | --- | --- |
| GitHub API | 5,000 calls an hour with a personal token | | |
| GitHub Actions | Schedules can start late; can be switched off after long repo inactivity | | |
| Hugging Face dataset | Check dataset size guidance | | |
| Hugging Face Spaces | 2 vCPU, 16 GB; sleeps after 48 h idle; disk not persistent | | |
| Neo4j AuraDB Free | 50,000 nodes, 175,000 relationships; pauses after 3 idle days | | |
| Neon Postgres | About 500 MB storage (unconfirmed in the plan) | | |
| Vercel | Rebuild after each refresh | | |
| deps.dev | Check terms and API quotas before bulk use | | |
