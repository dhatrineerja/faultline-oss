# Layer 6: Serving stores

Upsert loaders that copy from the lake into the store each access pattern needs. Both stores can be rebuilt from the lake.

| Store | Holds | Stage |
| --- | --- | --- |
| Neo4j AuraDB Free | The graph, for interactive path queries | 4 |
| Neon Postgres + pgvector | Embeddings plus copied scores | 5 |

**Done when:** Neo4j node and edge counts stay under 80% of the cap, and every tracked package has an embedding and current scores in Neon, with filters working in the same query.
