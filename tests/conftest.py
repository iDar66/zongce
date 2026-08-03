# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIX

def need(path: Path) -> Path:
    """fixture 缺失则 skip（本机未跑 populate_fixtures.py）。"""
    if not path.exists():
        pytest.skip(f"fixture 缺失，先跑 python tests/populate_fixtures.py：{path}")
    return path
