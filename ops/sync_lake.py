"""Download the lake from the private Hugging Face dataset into data/lake (or --dir).

Only the tables the score models read are fetched; run records, state files and the replaced
merged_prs table are skipped. Files already present and unchanged are not downloaded again.

Run from the repository root:  .venv/Scripts/python ops/sync_lake.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from huggingface_hub import snapshot_download

from faultline.env import load_dotenv, token

TABLES = ["backfill", "events_api", "pypi", "refresh", "refresh_reach", "repo_meta"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="data/lake", help="where to put the lake")
    args = parser.parse_args()
    load_dotenv()
    snapshot_download(
        repo_id=token("HF_DATASET_REPO"),
        repo_type="dataset",
        token=token("HF_TOKEN"),
        local_dir=args.dir,
        allow_patterns=[f"{t}/**" for t in TABLES] + ["state/refresh.json"],
    )
    print(f"lake synced to {args.dir}")


if __name__ == "__main__":
    main()
