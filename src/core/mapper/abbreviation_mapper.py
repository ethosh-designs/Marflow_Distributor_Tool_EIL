from __future__ import annotations

from dataclasses import dataclass, field

from src.core.grammar.registry import GrammarDefinition
from src.core.parser.feature_extractor import ExtractedFeatures


@dataclass
class MappedSegments:
	values: dict[str, str] = field(default_factory=dict)
	unresolved: list[str] = field(default_factory=list)


def _match_variant_code(
	features: ExtractedFeatures,
	variants_sample: dict[str, str],
) -> str | None:
	if not variants_sample:
		return None

	scored: list[tuple[int, str]] = []
	joined_tokens = set(features.tokens).union(features.bracket_tokens).union(features.type_hints)
	if features.color:
		joined_tokens.add(features.color)
	if features.premium:
		joined_tokens.add("PREMIUM")

	for code, label in variants_sample.items():
		label_tokens = {
			token
			for token in label.upper().replace("(", " ").replace(")", " ").replace("-", " ").split()
			if token
		}
		score = len(label_tokens.intersection(joined_tokens))
		scored.append((score, str(code)))

	scored.sort(key=lambda item: item[0], reverse=True)
	if not scored or scored[0][0] == 0:
		return None
	return scored[0][1]


def _match_by_label(options: dict[str, str], text: str) -> str | None:
	text_upper = text.upper()
	for code, label in options.items():
		if text_upper in label.upper():
			return str(code)
	return None


def _resolve_uc_variant(features: ExtractedFeatures, options: dict[str, str]) -> str | None:
	# Deterministic mapping from refined domain rule-set.
	# OPEN END -> 10, CONE TIP -> 13, BULB TIP -> 14.
	if features.cone_tip:
		if "13" in options:
			return "13"
		match = _match_by_label(options, "CONE TIP")
		if match is not None:
			return match

	if features.bulb_tip:
		if "14" in options:
			return "14"
		match = _match_by_label(options, "BULB TIP")
		if match is not None:
			return match

	if features.open_end:
		if "10" in options:
			return "10"
		match = _match_by_label(options, "OPEN END")
		if match is not None:
			return match

	return None


def map_features_to_segments(features: ExtractedFeatures, grammar: GrammarDefinition) -> MappedSegments:
	mapped = MappedSegments()

	for segment in grammar.segments:
		name = segment.name
		desc = grammar.segments_map.get(name)

		if name == "DD" and features.size_fr is not None:
			mapped.values[name] = str(features.size_fr).zfill(2)
			continue
		if name == "dd" and features.size_fr is not None:
			mapped.values[name] = str(features.size_fr).zfill(2)
			continue
		if name == "LL" and features.length_cm is not None:
			mapped.values[name] = str(features.length_cm).zfill(2)
			continue
		if name == "AA":
			for token in features.tokens:
				if token.isdigit() and 0 <= int(token) <= 90:
					mapped.values[name] = str(int(token)).zfill(2)
					break
			continue

		if isinstance(desc, dict):
			normalized_options = {str(k).upper(): str(k) for k in desc}
			string_options = {str(k): str(v) for k, v in desc.items()}

			if name == "V" and "UC" in grammar.template:
				uc_variant = _resolve_uc_variant(features, string_options)
				if uc_variant is not None:
					mapped.values[name] = uc_variant
					continue

			if name in {"V", "X"}:
				if "H" in normalized_options and features.coating_hydrophilic:
					mapped.values[name] = normalized_options["H"]
					continue
				if "S" in normalized_options and "SHORT" in features.tokens:
					mapped.values[name] = normalized_options["S"]
					continue
				if "L" in normalized_options and "LONG" in features.tokens:
					mapped.values[name] = normalized_options["L"]
					continue
				if "A" in normalized_options:
					mapped.values[name] = normalized_options["A"]
					continue

			candidate = _match_variant_code(features, string_options)
			if candidate is not None:
				mapped.values[name] = candidate
				continue

			# Deterministic fallback to first available option.
			mapped.values[name] = str(next(iter(desc.keys())))
			continue

		if name == "H" and features.coating_hydrophilic:
			mapped.values[name] = "H"
			continue

		if len(name) in {1, 2, 3} and name.isalpha() and name.upper() == name:
			mapped.values[name] = name
			continue

		if segment.is_dynamic and name not in mapped.values:
			mapped.unresolved.append(name)

	# If template carries explicit 00 placeholder and variants_sample exists, resolve it.
	if "00" in grammar.template and "00" not in mapped.values:
		variant_code = _match_variant_code(features, grammar.variants_sample)
		mapped.values["00"] = variant_code or "00"

	return mapped
