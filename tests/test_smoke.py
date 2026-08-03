import pytest
from conftest import need  # noqa
from pathlib import Path

def test_package_imports():
    import zongce  # noqa: F401

def test_fixtures_present(fixtures_dir):
    names = {p.name for p in fixtures_dir.iterdir()}
    assert "2026年河源校区计科杯篮球比赛参赛证明(盖章版).pdf" in names
