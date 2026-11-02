"""Per-run records: one small JSON file per ingestion run, stored in the lake under metrics/.

A record holds the counts, the rate-limit headroom, the repos that need attention (missing,
failed, gapped) and the lake size, so the dashboard and the runbook can read them later.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from faultline.env import token


def lake_size() -> dict:
    """File count and total bytes of the Hugging Face dataset; empty if it cannot be read."""
    from huggingface_hub import HfApi
    from huggingface_hub.errors import HfHubHTTPError

    try:
        info = HfApi(token=token("HF_TOKEN")).dataset_info(
            token("HF_DATASET_REPO"), files_metadata=True
        )
        sizes = [s.size or 0 for s in info.siblings]
        return {"lake_files": len(sizes), "lake_bytes": sum(sizes)}
    except (HfHubHTTPError, OSError, RuntimeError) as exc:  # never fail a run over a size lookup
        return {"lake_size_error": type(exc).__name__}


def write_run_record(root: Path, job: str, record: dict) -> tuple[Path, str]:
    """Write the record under root/metrics/<job>/date=YYYY-MM-DD/ and return (path, repo path)."""
    now = datetime.now(UTC)
    record = {"job": job, "finished_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), **record}
    rel = f"metrics/{job}/date={now:%Y-%m-%d}/run-{now:%H%M%S}.json"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, separators=(",", ":")), encoding="utf-8")
    return path, rel


def describe(record: dict) -> str:
    """One log line with the headroom, so every run shows how close to the limit it got."""
    headroom = record.get("rate_remaining_min")
    return (
        f"rate-limit headroom {headroom if headroom is not None else 'unknown'}; "
        f"gaps {len(record.get('gap_repos', []))}, missing {len(record.get('missing_repos', []))}, "
        f"failed {len(record.get('failed_repos', []))}"
    )
