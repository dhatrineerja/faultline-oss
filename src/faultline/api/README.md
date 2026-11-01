# Layer 7: Recommendation API

FastAPI in Docker on Hugging Face Spaces. Read-only and cached.

Request path: embed the query with fastembed, run one Postgres query (vector search, licence and language filters, ordering by copied scores), ask Neo4j only for the top few results' risk paths, then fill the explanation template. Every sentence of an explanation traces to a score component; no language model is involved.

**Built in:** Stage 5.

**Done when:** endpoints are documented, p95 is under 1 second when warm, and cold start is measured and shown.
