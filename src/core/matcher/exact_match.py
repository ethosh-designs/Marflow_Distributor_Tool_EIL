from __future__ import annotations

from src.core.grammar.validator import MasterRecord, MasterValidator


def find_exact_code(candidate_code: str, validator: MasterValidator) -> MasterRecord | None:
	return validator.get(candidate_code)
