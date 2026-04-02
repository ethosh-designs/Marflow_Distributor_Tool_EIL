from __future__ import annotations

from src.core.grammar.registry import GrammarDefinition


def build_code(grammar: GrammarDefinition, mapped_segments: dict[str, str]) -> str:
	parts: list[str] = []

	for segment in grammar.segments:
		key = segment.name
		if key in mapped_segments:
			value = mapped_segments[key]
		elif key in grammar.segments_map and not segment.is_dynamic:
			value = key
		else:
			value = "".join("0" for _ in range(segment.width))

		parts.append(value)

	return "".join(parts).upper()
