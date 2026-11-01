# Layer 5: Graph compute

NetworkX computes PageRank and transitive dependency risk inside the pipeline and writes the results back into the marts. Heavy graph maths runs offline, so the dashboard and ranking get it without calling Neo4j.

**Built in:** Stage 4.

**Done when:** counts are within the Neo4j cap, and the "low-activity dependency three levels down" query returns real examples.
