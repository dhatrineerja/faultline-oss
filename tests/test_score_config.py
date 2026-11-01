import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"


def test_score_weights_sum_to_100():
    for path in CONFIG_DIR.glob("score_*.toml"):
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        assert sum(config["weights"].values()) == 100, path.name
