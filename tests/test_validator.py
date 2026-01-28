import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.connectors import validator


def test_validator_accepts_valid():
    assert validator.validate_event({"type": "push", "repo": "r/x"})


def test_validator_rejects_invalid():
    assert not validator.validate_event(None)
    assert not validator.validate_event({})
