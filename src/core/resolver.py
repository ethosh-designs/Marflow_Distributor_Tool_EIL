from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.compiler.code_builder import build_code
from src.core.grammar.loader import GrammarLoader
from src.core.grammar.registry import GrammarRegistry
from src.core.grammar.validator import MasterValidator
from src.core.mapper.abbreviation_mapper import map_features_to_segments
from src.core.matcher.exact_match import find_exact_code
from src.core.matcher.scoring_engine import best_fallback_match, filter_records, score_record
from src.core.parser.family_detector import detect_family
from src.core.parser.feature_extractor import extract_features


@dataclass
class ResolveResult:
	input_description: str
	resolved_code: str
	method: str
	confidence: str

	def as_dict(self) -> dict[str, Any]:
		return {
			"input_description": self.input_description,
			"resolved_code": self.resolved_code,
			"method": self.method,
			"confidence": self.confidence,
		}


def _default_paths() -> tuple[Path, Path]:
	root = Path(__file__).resolve().parents[2]
	grammar_path = root / "data" / "raw" / "index_docs.json"
	master_path = root / "data" / "raw" / "master_list.xlsx"
	return grammar_path, master_path


class ProductCodeResolver:
	def __init__(
		self,
		grammar_path: str | Path | None = None,
		master_path: str | Path | None = None,
	) -> None:
		default_grammar, default_master = _default_paths()
		grammar_file = Path(grammar_path) if grammar_path else default_grammar
		master_file = Path(master_path) if master_path else default_master

		self._loader = GrammarLoader(grammar_file)
		grammar_json = self._loader.load()
		self._registry = GrammarRegistry(grammar_json)
		self._validator = MasterValidator(master_file)

	def resolve(self, description: str) -> dict[str, Any]:
		features = extract_features(description)
		family_match = detect_family(features.normalized, self._registry.all())
		grammar = self._registry.get(family_match.grammar_template)

		mapped = map_features_to_segments(features, grammar)
		candidate_code = build_code(grammar, mapped.values)

		exact = find_exact_code(candidate_code, self._validator)
		if exact is not None:
			return ResolveResult(
				input_description=description,
				resolved_code=exact.product_code,
				method="constructed",
				confidence="high",
			).as_dict()

		constrained = filter_records(self._validator.all(), family_match.family_name, features)
		fallback = best_fallback_match(constrained, features)

		if fallback is None:
			return ResolveResult(
				input_description=description,
				resolved_code="",
				method="matched",
				confidence="low",
			).as_dict()

		fallback_score = score_record(fallback, features)
		confidence = "medium" if fallback_score >= 4 else "low"

		return ResolveResult(
			input_description=description,
			resolved_code=fallback.product_code,
			method="matched",
			confidence=confidence,
		).as_dict()
