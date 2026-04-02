from __future__ import annotations

from pathlib import Path

from src.core.grammar.validator import MasterValidator


def create_master_validator(master_path: str | Path) -> MasterValidator:
    return MasterValidator(master_path)
