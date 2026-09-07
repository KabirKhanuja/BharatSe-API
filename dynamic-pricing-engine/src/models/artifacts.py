from __future__ import annotations
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

from src.config import MODELS_DIR


MODEL_VERSION = "v1"


class ArtefactsNotFoundError(FileNotFoundError):
    pass


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _save_model(model: Any, path: Path) -> bytes:
    booster = getattr(model, "booster_", None)
    if booster is not None:
        booster.save_model(str(path))
        with open(path, "rb") as f:
            return f.read()
    b = pickle.dumps(model)
    path.write_bytes(b)
    return b


def _load_model(path: Path) -> Any:
    if path.suffix == ".txt":
        import lightgbm as lgb
        try:
            return lgb.Booster(model_file=str(path))
        except Exception:
            pass
    try:
        return pickle.loads(path.read_bytes())
    except Exception:
        pass
    import lightgbm as lgb
    booster = lgb.Booster(model_file=str(path))
    return booster


def build_manifest(models: dict, columns: list, levels: dict, imputation: dict) -> dict:
    models_meta = {}
    for name, model in models.items():
        filename = f"lgbm_{name}.txt"
        try:
            blob = pickle.dumps(model)
        except Exception:
            try:
                import lightgbm as lgb
                blob = model.booster_.model_to_string().encode("utf-8") if hasattr(model, "booster_") else b""
            except Exception:
                blob = b""
        sha = _sha256_bytes(blob) if blob else ""
        models_meta[name] = {"path": filename, "sha256": sha}
    return {
        "version": MODEL_VERSION,
        "feature_columns": list(columns),
        "categorical_levels": {k: list(v) for k, v in levels.items()},
        "imputation": dict(imputation),
        "models": models_meta,
    }


def save_artifacts(models: dict, columns: list, levels: dict, imputation: dict, path,
                  market_buckets=None) -> dict:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(models, columns, levels, imputation)
    if market_buckets is not None:
        manifest["market_buckets"] = {"path": "market_buckets.parquet"}
    for name, model in models.items():
        file_path = path / f"lgbm_{name}.txt"
        blob = _save_model(model, file_path)
        manifest["models"][name]["sha256"] = _sha256_bytes(blob)
    if market_buckets is not None:
        try:
            market_buckets.to_parquet(path / "market_buckets.parquet")
        except Exception:
            import pickle
            (path / "market_buckets.pkl").write_bytes(pickle.dumps(market_buckets))
            manifest["market_buckets"] = {"path": "market_buckets.pkl"}
    manifest_path = path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
    return manifest_path


def load_artifacts(path) -> dict:
    path = Path(path)
    if not path.is_dir():
        raise ArtefactsNotFoundError(f"Artefacts directory not found: {path}")
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise ArtefactsNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    models = {name: _load_model(path / meta["path"]) for name, meta in manifest["models"].items()}
    out = {
        **models,
        "feature_columns": manifest.get("feature_columns", []),
        "categorical_levels": manifest.get("categorical_levels", {}),
        "imputation": manifest.get("imputation", {}),
        "version": manifest.get("version", MODEL_VERSION),
    }
    mb_meta = manifest.get("market_buckets")
    if mb_meta:
        mb_path = path / mb_meta["path"]
        if mb_path.exists():
            try:
                import pandas as pd
                out["market_buckets"] = pd.read_parquet(mb_path)
            except Exception:
                import pickle
                out["market_buckets"] = pickle.loads(mb_path.read_bytes())
    return out
