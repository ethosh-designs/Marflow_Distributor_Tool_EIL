from __future__ import annotations

import re
from dataclasses import dataclass, field


_FR_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*FR", re.IGNORECASE)
_CM_RE = re.compile(r"(\d{1,3})\s*CM", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\(([^\)]*)\)")


@dataclass
class ExtractedFeatures:
	raw_description: str
	normalized: str
	tokens: set[str] = field(default_factory=set)
	bracket_tokens: set[str] = field(default_factory=set)
	size_fr: int | None = None
	length_cm: int | None = None
	color: str | None = None
	coating_hydrophilic: bool = False
	open_end: bool = False
	cone_tip: bool = False
	bulb_tip: bool = False
	with_stylet: bool = False
	curved: bool = False
	premium: bool = False
	type_hints: set[str] = field(default_factory=set)


def _normalize_description(text: str) -> str:
	text = text.upper()
	text = text.replace("-", " ")
	text = text.replace("/", " ")
	text = text.replace(",", " ")
	text = re.sub(r"\s+", " ", text).strip()
	return text


def _extract_bracket_tokens(text: str) -> set[str]:
	tokens: set[str] = set()
	for group in _BRACKET_RE.findall(text):
		for part in group.split("-"):
			piece = part.strip().upper()
			if piece:
				tokens.add(piece)
				for word in piece.split():
					tokens.add(word)
	return tokens


def _extract_numeric(text: str, regex: re.Pattern[str]) -> int | None:
	match = regex.search(text)
	if not match:
		return None
	return int(float(match.group(1)))


def extract_features(description: str) -> ExtractedFeatures:
	bracket_tokens = _extract_bracket_tokens(description.upper())
	normalized = _normalize_description(description)
	tokens = {token for token in normalized.split(" ") if token}

	size_fr = _extract_numeric(normalized, _FR_RE)
	length_cm = _extract_numeric(normalized, _CM_RE)

	color = None
	for candidate in ("BLUE", "GREEN", "WHITE", "YELLOW", "BLACK"):
		if candidate in tokens or candidate in bracket_tokens:
			color = candidate
			break

	coating_hydrophilic = "HYDROPHILIC" in tokens or "HYDROPHILIC" in bracket_tokens
	open_end = (
		("OPEN" in tokens and "END" in tokens)
		or "OPEN END" in bracket_tokens
		or "OE" in tokens
		or ("OPEN" in bracket_tokens and "END" in bracket_tokens)
	)
	cone_tip = (
		("CONE" in tokens and "TIP" in tokens)
		or "CONE TIP" in bracket_tokens
		or ("CONE" in bracket_tokens and "TIP" in bracket_tokens)
	)
	bulb_tip = (
		("BULB" in tokens and "TIP" in tokens)
		or "BULB TIP" in bracket_tokens
		or ("BULB" in bracket_tokens and "TIP" in bracket_tokens)
	)
	with_stylet = (
		("WITH" in tokens and "STYLET" in tokens)
		or "WITH STYLET" in bracket_tokens
		or "STYLET" in tokens
	)
	curved = "CURVED" in tokens
	premium = "PREMIUM" in tokens or "PREMIUM" in bracket_tokens

	type_hints: set[str] = set()
	for token in tokens.union(bracket_tokens):
		if token in {"CE", "BEO", "BEML", "BP", "RP", "GP", "BLP", "OEML"}:
			type_hints.add(token)

	return ExtractedFeatures(
		raw_description=description,
		normalized=normalized,
		tokens=tokens,
		bracket_tokens=bracket_tokens,
		size_fr=size_fr,
		length_cm=length_cm,
		color=color,
		coating_hydrophilic=coating_hydrophilic,
		open_end=open_end,
		cone_tip=cone_tip,
		bulb_tip=bulb_tip,
		with_stylet=with_stylet,
		curved=curved,
		premium=premium,
		type_hints=type_hints,
	)
