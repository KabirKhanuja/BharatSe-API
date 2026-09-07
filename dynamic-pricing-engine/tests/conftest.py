from __future__ import annotations
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture(scope="session")
def fashion_dir(data_dir: Path) -> Path:
    return data_dir / "indian_fashion_ecommerce"


@pytest.fixture(scope="session")
def ecommerce_csv(data_dir: Path) -> Path:
    return data_dir / "ecommerce_customer_behavior" / "Ecommerce.csv"


@pytest.fixture(scope="session")
def odop_csv(data_dir: Path) -> Path:
    return data_dir / "odop" / "20250707_ODOP_Products_V31.csv"


@pytest.fixture(scope="session")
def synthetic_market_csv(data_dir: Path) -> Path:
    return data_dir / "synthetic" / "dynamic_pricing_synthetic_market.csv"


@pytest.fixture(scope="session")
def synthetic_raw_material_csv(data_dir: Path) -> Path:
    return data_dir / "synthetic" / "dynamic_pricing_synthetic_raw_material.csv"


@pytest.fixture(scope="session")
def synthetic_regional_craft_csv(data_dir: Path) -> Path:
    return data_dir / "synthetic" / "dynamic_pricing_synthetic_regional_craft.csv"
