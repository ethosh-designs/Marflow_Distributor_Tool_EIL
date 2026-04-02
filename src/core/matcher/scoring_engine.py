from __future__ import annotations

import re

from src.core.grammar.validator import MasterRecord
from src.core.parser.feature_extractor import ExtractedFeatures


_FR_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*FR", re.IGNORECASE)
_CM_RE = re.compile(r"(\d{1,3})\s*CM", re.IGNORECASE)


def _extract_number(regex: re.Pattern[str], text: str) -> int | None:
	hit = regex.search(text)
	if not hit:
		return None
	return int(float(hit.group(1)))


def filter_records(
	records: list[MasterRecord],
	family_name: str,
	features: ExtractedFeatures,
) -> list[MasterRecord]:
	family_tokens = set(family_name.upper().replace("-", " ").split())

	filtered: list[MasterRecord] = []
	for record in records:
		desc_tokens = set(record.product_description.split())
		if not family_tokens.intersection(desc_tokens):
			continue

		if features.size_fr is not None:
			record_fr = _extract_number(_FR_RE, record.product_description)
			if record_fr is not None and record_fr != features.size_fr:
				continue

		if features.length_cm is not None:
			record_cm = _extract_number(_CM_RE, record.product_description)
			if record_cm is not None and record_cm != features.length_cm:
				continue

		filtered.append(record)

	return filtered


def score_record(record: MasterRecord, features: ExtractedFeatures) -> int:
	score = 0
	desc = record.product_description
	tokens = set(desc.split())

	if features.color and features.color in tokens:
		score += 3
	if features.coating_hydrophilic and "HYDROPHILIC" in tokens:
		score += 3
	if features.open_end and "OPEN" in tokens and "END" in tokens:
		score += 2
	if features.curved and "CURVED" in tokens:
		score += 1
	if features.premium and "PREMIUM" in tokens:
		score += 1

	for hint in features.type_hints:
		if hint in desc:
			score += 1

	return score


def best_fallback_match(records: list[MasterRecord], features: ExtractedFeatures) -> MasterRecord | None:
	if not records:
		return None

	ranked = sorted(records, key=lambda record: score_record(record, features), reverse=True)
	return ranked[0]
