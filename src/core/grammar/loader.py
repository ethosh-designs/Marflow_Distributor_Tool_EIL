from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(path: str | Path) -> dict[str, Any]:
	file_path = Path(path)
	if not file_path.exists():
		raise FileNotFoundError(f"Grammar file not found: {file_path}")

	with file_path.open("r", encoding="utf-8") as handle:
		data = json.load(handle)

	if not isinstance(data, dict):
		raise ValueError("Grammar JSON must contain an object at root level")

	return data


class GrammarLoader:
	def __init__(self, grammar_path: str | Path) -> None:
		self._path = Path(grammar_path)
		self._cache: dict[str, Any] | None = None

	def load(self, force_reload: bool = False) -> dict[str, Any]:
		if self._cache is None or force_reload:
			self._cache = load_json_file(self._path)
		return self._cache
