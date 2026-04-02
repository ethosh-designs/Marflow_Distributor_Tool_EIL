from __future__ import annotations

from src.core.grammar.registry import GrammarDefinition


def explain_segments(grammar: GrammarDefinition, values: dict[str, str]) -> dict[str, str]:
	explanation: dict[str, str] = {}
	for segment in grammar.segments:
		key = segment.name
		chosen = values.get(key)
		if chosen is None:
			continue

		desc = grammar.segments_map.get(key)
		if isinstance(desc, dict):
			explanation[key] = str(desc.get(chosen, chosen))
		else:
			explanation[key] = str(desc) if desc else chosen
	return explanation
