"""Date- and hour-partitioned Parquet lake. A write replaces its whole partition."""

import os
from datetime import date
from pathlib import Path

EVENTS = "events"


def lake_dir() -> Path:
    return Path(os.environ.get("LAKE_LOCAL_DIR", "data/lake"))


def partition_path(root: Path, table: str, day: date, hour: int) -> Path:
    return root / table / f"date={day.isoformat()}" / f"hour={hour:02d}" / "part.parquet"


def upload_partition(local: Path, root: Path) -> None:
    """Copy one partition file to the Hugging Face dataset, replacing the file at that path."""
    from huggingface_hub import HfApi

    api = HfApi(token=os.environ["HF_TOKEN"])
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=local.relative_to(root).as_posix(),
        repo_id=os.environ["HF_DATASET_REPO"],
        repo_type="dataset",
    )
