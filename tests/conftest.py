"""
Shared Pytest Fixtures and Environment Configuration
"""

import json
import os
import sys
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Ensure scripts directory is in python search path
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pubchem_api import PubChemClient


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def mock_dataset_path() -> Path:
    return ASSETS_DIR / "synthetic_mocks.json"


@pytest.fixture(scope="session")
def mock_data(mock_dataset_path: Path) -> dict:
    with open(mock_dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_client() -> PubChemClient:
    return PubChemClient(mock_fallback=True)
