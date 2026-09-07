from __future__ import annotations
from pathlib import Path
import json
import shutil
import pytest

from src.models.artifacts import save_artifacts, load_artifacts, build_manifest, ArtefactsNotFoundError


def _train_dummy_models():
    import lightgbm as lgb
    import numpy as np
    rng = np.random.default_rng(42)
    X = rng.normal(size=(200, 5))
    y = rng.normal(size=200) * 100 + 2500
    feature_names = [f"f{i}" for i in range(5)]
    X = __import__("pandas").DataFrame(X, columns=feature_names)
    p50 = lgb.LGBMRegressor(n_estimators=20, random_state=42, verbose=-1)
    p50.fit(X, y)
    p10 = lgb.LGBMRegressor(objective="quantile", alpha=0.10, n_estimators=20, random_state=42, verbose=-1)
    p10.fit(X, y)
    p50q = lgb.LGBMRegressor(objective="quantile", alpha=0.50, n_estimators=20, random_state=42, verbose=-1)
    p50q.fit(X, y)
    p90 = lgb.LGBMRegressor(objective="quantile", alpha=0.90, n_estimators=20, random_state=42, verbose=-1)
    p90.fit(X, y)
    return {"p50": p50, "p10": p10, "p50_quantile": p50q, "p90": p90}, feature_names


def test_build_manifest_has_required_keys():
    models, cols = _train_dummy_models()
    levels = {"category": ["Saree", "Bag", "__missing__"]}
    imputation = {"raw_material_cost_inr": 0.0, "labour_cost_inr": 0.0}
    manifest = build_manifest(models, cols, levels, imputation)
    for k in ("version", "feature_columns", "categorical_levels", "imputation", "models"):
        assert k in manifest
    for m in ("p50", "p10", "p50_quantile", "p90"):
        assert m in manifest["models"]
        assert "sha256" in manifest["models"][m]
        assert "path" in manifest["models"][m]


def test_save_artifacts_writes_files(tmp_path: Path):
    models, cols = _train_dummy_models()
    levels = {"category": ["Saree", "Bag", "__missing__"]}
    imputation = {"raw_material_cost_inr": 0.0}
    out = tmp_path / "models_v1"
    manifest_path = save_artifacts(models, cols, levels, imputation, out)
    assert (out / "manifest.json").exists()
    assert (out / "lgbm_p50.txt").exists()
    assert (out / "lgbm_p10.txt").exists()
    assert (out / "lgbm_p50_quantile.txt").exists()
    assert (out / "lgbm_p90.txt").exists()
    assert manifest_path == out / "manifest.json"


def test_load_artifacts_round_trip(tmp_path: Path):
    models, cols = _train_dummy_models()
    levels = {"category": ["Saree", "Bag", "__missing__"]}
    imputation = {"raw_material_cost_inr": 0.0}
    out = tmp_path / "models_v1"
    save_artifacts(models, cols, levels, imputation, out)
    loaded = load_artifacts(out)
    for k in ("p50", "p10", "p50_quantile", "p90", "feature_columns", "categorical_levels"):
        assert k in loaded


def test_load_artifacts_missing_directory(tmp_path: Path):
    with pytest.raises(ArtefactsNotFoundError):
        load_artifacts(tmp_path / "does_not_exist")


def test_manifest_sha256_is_stable(tmp_path: Path):
    models, cols = _train_dummy_models()
    levels = {"category": ["Saree"]}
    imputation = {}
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    save_artifacts(models, cols, levels, imputation, out1)
    save_artifacts(models, cols, levels, imputation, out2)
    m1 = json.loads((out1 / "manifest.json").read_text())
    m2 = json.loads((out2 / "manifest.json").read_text())
    assert m1["models"]["p50"]["sha256"] == m2["models"]["p50"]["sha256"]
