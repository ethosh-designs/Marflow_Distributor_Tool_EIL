from __future__ import annotations

from dataclasses import dataclass

from src.core.grammar.registry import GrammarDefinition


@dataclass(frozen=True)
class FamilyMatch:
	family_name: str
	grammar_template: str
	score: int


_FAMILY_RULES: list[tuple[tuple[str, ...], tuple[str, ...], str]] = [
	(("DOUBLE", "J", "STENT"), (), "DOUBLE J STENT"),
	(("MONO", "J", "STENT"), (), "MONO J STENT CATHETER"),
	(("STONE", "BASKET"), (), "STONE BASKET"),
	(("G", "PAW"), (), "G-PAW BASKET"),
	(("STONE", "GRASPER"), (), "STONE GRASPER"),
	(("URETERAL", "ACCESS", "SHEATH"), (), "URETERAL ACCESS SHEATH"),
	(("DUAL", "LUMEN"), (), "DUAL LUMEN URETERAL CATHETER"),
	(("AMPLATZ", "SHEATH", "WITH", "DILATOR"), (), "AMPLATZ SHEATH WITH DILATOR"),
	(("AMPLATZ", "RENAL", "DILATOR", "SET"), (), "AMPLATZ RENAL DILATOR SET"),
	(("AMPLATZ", "DILATOR"), ("SET",), "AMPLATZ DILATOR"),
	(("AMPLATZ", "SHEATH"), ("WITH", "DILATOR"), "AMPLATZ SHEATH"),
	(("GUIDE", "WIRE"), (), "GUIDE WIRE"),
	(("CATHETER",), ("BALLOON",), "CYSTO CATHETER & SET"),
	(("BALLOON", "CATHETER"), (), "INTEGRAL BALLOON CATHETER"),
]


def _tokenize(text: str) -> set[str]:
	return {part for part in text.upper().replace("-", " ").replace("/", " ").split() if part}


def detect_family(description: str, grammar_definitions: list[GrammarDefinition]) -> FamilyMatch:
	tokens = _tokenize(description)
	by_name = {definition.name.upper(): definition for definition in grammar_definitions}

	best: FamilyMatch | None = None
	for include_tokens, exclude_tokens, family_name in _FAMILY_RULES:
		family_upper = family_name.upper()
		if family_upper not in by_name:
			continue
		if any(token not in tokens for token in include_tokens):
			continue
		if any(token in tokens for token in exclude_tokens):
			continue

		score = len(include_tokens)
		candidate = FamilyMatch(
			family_name=family_name,
			grammar_template=by_name[family_upper].template,
			score=score,
		)
		if best is None or candidate.score > best.score:
			best = candidate

	if best is not None:
		return best

	# Deterministic fallback: choose first grammar family with highest token overlap.
	max_overlap = -1
	fallback_match: FamilyMatch | None = None
	for definition in grammar_definitions:
		name_tokens = _tokenize(definition.name)
		overlap = len(tokens.intersection(name_tokens))
		if overlap > max_overlap:
			max_overlap = overlap
			fallback_match = FamilyMatch(
				family_name=definition.name,
				grammar_template=definition.template,
				score=overlap,
			)

	if fallback_match is None:
		raise ValueError("No grammar definitions available for family detection")

	return fallback_match
