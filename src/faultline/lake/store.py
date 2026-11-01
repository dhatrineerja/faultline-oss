"""Date- and hour-partitioned Parquet lake. A write replaces its whole partition."""

import os
from datetime import date
from pathlib import Path

from faultline.env import token

EVENTS = "events"


def lake_dir() -> Path:
    return Path(os.environ.get("LAKE_LOCAL_DIR", "data/lake"))


def partition_path(root: Path, table: str, day: date, hour: int) -> Path:
    return root / table / f"date={day.isoformat()}" / f"hour={hour:02d}" / "part.parquet"


def upload_partition(local: Path, root: Path) -> None:
    """Copy one partition file to the Hugging Face dataset, replacing the file at that path."""
    from huggingface_hub import HfApi

    api = HfApi(token=token("HF_TOKEN"))
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=local.relative_to(root).as_posix(),
        repo_id=token("HF_DATASET_REPO"),
        repo_type="dataset",
    )


def _api():
    from huggingface_hub import HfApi

    return HfApi(token=token("HF_TOKEN"))


def fetch(rel: str, local_dir: Path) -> bool:
    """Download one file of the dataset to local_dir/rel; False if the dataset has no such file."""
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import EntryNotFoundError

    try:
        hf_hub_download(
            repo_id=token("HF_DATASET_REPO"),
            filename=rel,
            repo_type="dataset",
            local_dir=local_dir,
            token=token("HF_TOKEN"),
        )
    except EntryNotFoundError:
        return False
    return True


def upload_batch(items: list[tuple[Path, str]], message: str, chunk: int = 400) -> None:
    """Commit many files to the dataset in a few commits. items are (local path, repo path)."""
    from huggingface_hub import CommitOperationAdd

    api = _api()
    for i in range(0, len(items), chunk):
        ops = [
            CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(path))
            for path, rel in items[i : i + chunk]
        ]
        api.create_commit(
            repo_id=token("HF_DATASET_REPO"),
            repo_type="dataset",
            operations=ops,
            commit_message=message,
        )
