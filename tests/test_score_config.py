import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"


def test_score_weights_sum_to_100():
    for path in CONFIG_DIR.glob("score_*.toml"):
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        assert sum(config["weights"].values()) == 100, path.name


def test_dbt_weights_match_the_score_formula_file():
    """The marts read weights from dbt_project.yml, so they must equal config/score_v1.toml."""
    import yaml

    project = yaml.safe_load(
        (CONFIG_DIR.parent / "transform" / "dbt_project.yml").read_text("utf-8")
    )
    formula = tomllib.loads((CONFIG_DIR / "score_v1.toml").read_text(encoding="utf-8"))
    assert project["vars"]["weights"] == formula["weights"]
    assert project["vars"]["window_days"] == formula["window_days"]
    assert project["vars"]["dependency_depth_discount"] == formula["dependency_depth_discount"]
    assert project["vars"]["score_formula_version"] == formula["version"]
