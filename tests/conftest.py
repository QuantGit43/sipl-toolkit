from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture
def example():
    def load(name: str) -> str:
        return (EXAMPLES / name).read_text(encoding="utf-8")
    return load
