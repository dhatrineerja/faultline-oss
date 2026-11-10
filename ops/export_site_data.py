"""Export the derived tables the dashboard reads: scores and a one-row freshness record.

Only package-level derived values leave the lake: no raw events, no people. Run after `dbt run`
and `dbt test`. Output goes to dashboard/sources/faultline/ as CSV.

Run from the repository root:  .venv/Scripts/python ops/export_site_data.py
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PUBLIC_COLUMNS = """
    package, repo, as_of, formula_version, status, confidence, n_components,
    round(score, 1) as score,
    graph_terms_included, is_archived, is_inactive,
    maintainer_activity, round(contributor_retention, 3) as contributor_retention,
    round(responsiveness_hours, 1) as responsiveness_hours, round(pr_flow, 3) as pr_flow,
    release_recency_days, bus_factor,
    round(pct_maintainer_activity, 1) as pct_maintainer_activity,
    round(pct_contributor_retention, 1) as pct_contributor_retention,
    round(pct_responsiveness, 1) as pct_responsiveness,
    round(pct_pr_flow, 1) as pct_pr_flow,
    round(pct_release_recency, 1) as pct_release_recency,
    round(pct_bus_factor, 1) as pct_bus_factor
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "data" / "faultline.duckdb"))
    parser.add_argument("--out", default=str(ROOT / "dashboard" / "sources" / "faultline"))
    parser.add_argument("--lake", default=str(ROOT / "data" / "lake"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db, read_only=True)

    con.execute(
        f"copy (select {PUBLIC_COLUMNS} from health_score order by package) "
        f"to '{(out / 'scores.csv').as_posix()}' (header, delimiter ',')"
    )
    lake = Path(args.lake)
    reach = con.execute(
        f"select max(reached_at) from read_parquet('{(lake / 'refresh_reach').as_posix()}/**/*.parquet')"
    ).fetchone()[0]
    state = json.loads((lake / "state" / "refresh.json").read_text(encoding="utf-8"))
    as_of, version = con.execute(
        "select max(as_of), max(formula_version) from health_score"
    ).fetchone()
    counts = dict(con.execute("select status, count(*) from health_score group by 1").fetchall())
    meta = {
        "built_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "as_of": str(as_of),
        "formula_version": version,
        "refresh_reached": str(reach),
        "repos_waiting": len(state.get("pending", {})),
        "packages": sum(counts.values()),
        "scored": counts.get("scored", 0),
        "dormant": counts.get("dormant", 0),
        "insufficient_data": counts.get("insufficient_data", 0),
        "unmapped": counts.get("unmapped", 0),
    }
    (out / "meta.csv").write_text(
        ",".join(meta) + "\n" + ",".join(str(v) for v in meta.values()) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
