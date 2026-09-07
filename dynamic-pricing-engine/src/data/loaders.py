from __future__ import annotations
from pathlib import Path
import pandas as pd


class DataSourceError(FileNotFoundError):
    pass


def _check_exists(path: Path) -> None:
    if not path.exists():
        raise DataSourceError(f"Data file not found: {path}")


def load_indian_fashion(data_dir: Path) -> pd.DataFrame:
    csvs = sorted(data_dir.glob("*.csv"))
    if not csvs:
        raise DataSourceError(f"No CSV files found in {data_dir}")
    frames = [pd.read_csv(p) for p in csvs]
    return pd.concat(frames, ignore_index=True)


def load_ecommerce(csv_path: Path) -> pd.DataFrame:
    _check_exists(csv_path)
    return pd.read_csv(csv_path)


def load_odop(csv_path: Path) -> pd.DataFrame:
    _check_exists(csv_path)
    return pd.read_csv(csv_path, encoding="latin-1")


def load_synthetic_market(csv_path: Path) -> pd.DataFrame:
    _check_exists(csv_path)
    return pd.read_csv(csv_path)


def load_synthetic_raw_material(csv_path: Path) -> pd.DataFrame:
    _check_exists(csv_path)
    return pd.read_csv(csv_path)


def load_synthetic_regional_craft(csv_path: Path) -> pd.DataFrame:
    _check_exists(csv_path)
    return pd.read_csv(csv_path)
