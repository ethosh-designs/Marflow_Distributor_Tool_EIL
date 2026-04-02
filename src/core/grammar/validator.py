from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class MasterRecord:
	product_code: str
	product_description: str


def _normalize_column_name(name: str) -> str:
	return str(name).strip().lower().replace(" ", "_")


def _load_table(path: Path) -> pd.DataFrame:
	suffix = path.suffix.lower()
	if suffix == ".csv":
		return pd.read_csv(path)
	if suffix in {".xlsx", ".xls"}:
		return pd.read_excel(path)
	if suffix == ".parquet":
		return pd.read_parquet(path)
	raise ValueError(f"Unsupported master file type: {suffix}")


class MasterValidator:
	def __init__(self, master_path: str | Path) -> None:
		self._path = Path(master_path)
		self._records: list[MasterRecord] = []
		self._by_code: dict[str, MasterRecord] = {}
		self._load()

	def _load(self) -> None:
		if not self._path.exists():
			raise FileNotFoundError(f"Master file not found: {self._path}")

		frame = _load_table(self._path)
		columns = {_normalize_column_name(col): col for col in frame.columns}

		code_col = columns.get("product_code") or columns.get("code")
		desc_col = columns.get("product_description") or columns.get("description")
		if not code_col or not desc_col:
			raise ValueError("Master file must contain product_code and product_description columns")

		rows = frame[[code_col, desc_col]].dropna()
		for row in rows.itertuples(index=False):
			code = str(row[0]).strip().upper()
			desc = str(row[1]).strip().upper()
			if not code:
				continue
			record = MasterRecord(product_code=code, product_description=desc)
			self._records.append(record)
			self._by_code[code] = record

	def exists(self, code: str) -> bool:
		return code.strip().upper() in self._by_code

	def get(self, code: str) -> MasterRecord | None:
		return self._by_code.get(code.strip().upper())

	def all(self) -> list[MasterRecord]:
		return list(self._records)

	def filter_codes(self, predicate: callable) -> list[MasterRecord]:
		return [record for record in self._records if predicate(record)]

	def first_existing(self, candidates: Iterable[str]) -> MasterRecord | None:
		for code in candidates:
			found = self.get(code)
			if found is not None:
				return found
		return None
