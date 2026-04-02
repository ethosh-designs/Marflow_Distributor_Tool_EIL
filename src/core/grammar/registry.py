from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SegmentSpec:
	name: str
	width: int
	description: str | dict[str, str]
	is_dynamic: bool
	is_selectable: bool


@dataclass(frozen=True)
class GrammarDefinition:
	template: str
	name: str
	notes: str
	segments: list[SegmentSpec]
	segments_map: dict[str, str | dict[str, str]]
	variants_sample: dict[str, str]


_NUMERIC_TOKEN_NAMES = {"DD", "dd", "LL", "AA", "CC"}


def _tokenize_template(template: str, known_segments: set[str]) -> list[str]:
	if not template:
		raise ValueError("Invalid grammar template: empty")

	ordered_candidates = sorted(known_segments.union({"00"}), key=len, reverse=True)
	tokens: list[str] = []
	idx = 0

	while idx < len(template):
		matched = None
		for candidate in ordered_candidates:
			if template.startswith(candidate, idx):
				matched = candidate
				break

		if matched is None:
			matched = template[idx]

		tokens.append(matched)
		idx += len(matched)

	return tokens


def _make_segment_specs(template: str, segments_map: dict[str, Any]) -> list[SegmentSpec]:
	specs: list[SegmentSpec] = []
	for token in _tokenize_template(template, set(segments_map.keys())):
		desc = segments_map.get(token, "")
		is_selectable = isinstance(desc, dict)
		is_dynamic = is_selectable or token in _NUMERIC_TOKEN_NAMES
		specs.append(
			SegmentSpec(
				name=token,
				width=len(token),
				description=desc,
				is_dynamic=is_dynamic,
				is_selectable=is_selectable,
			)
		)
	return specs


class GrammarRegistry:
	def __init__(self, grammar_json: dict[str, Any]) -> None:
		self._definitions: dict[str, GrammarDefinition] = {}
		self._load(grammar_json)

	def _load(self, grammar_json: dict[str, Any]) -> None:
		for template, payload in grammar_json.items():
			segments_map = payload.get("segments", {})
			definition = GrammarDefinition(
				template=template,
				name=str(payload.get("name", template)),
				notes=str(payload.get("notes", "")),
				segments=_make_segment_specs(template, segments_map),
				segments_map=segments_map,
				variants_sample=payload.get("variants_sample", {}),
			)
			self._definitions[template] = definition

	def get(self, template: str) -> GrammarDefinition:
		try:
			return self._definitions[template]
		except KeyError as exc:
			raise KeyError(f"Unknown grammar template: {template}") from exc

	def all(self) -> list[GrammarDefinition]:
		return list(self._definitions.values())
