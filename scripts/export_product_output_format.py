from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def _normalize_col(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def _parse_diameter(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text or text == "NAN":
        return ""
    hit = re.search(r"\d+(?:\.\d+)?", text)
    if not hit:
        return ""
    number = float(hit.group(0))
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _parse_length_mm(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text or text == "NAN":
        return ""

    hit = re.search(r"\d+(?:\.\d+)?", text)
    if not hit:
        return ""

    number = float(hit.group(0))
    if "CM" in text:
        number *= 10.0

    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _extract_sheet(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {_normalize_col(col): col for col in df.columns}

    code_col = col_map.get("PRODUCTCODE")
    name_col = col_map.get("PRODUCTNAME") or col_map.get("PRODUCTDESCRIPTION")
    size_col = col_map.get("SIZE")
    length_col = col_map.get("LENGTH")

    if not code_col or not name_col:
        return pd.DataFrame(columns=["Particular", "Diameter Range", "Length(mm)", "Product Code"])

    if not size_col:
        df["__size__"] = ""
        size_col = "__size__"
    if not length_col:
        df["__length__"] = ""
        length_col = "__length__"

    out = pd.DataFrame(
        {
            "Particular": df[name_col].fillna("").astype(str).str.strip(),
            "Diameter Range": df[size_col].apply(_parse_diameter),
            "Length(mm)": df[length_col].apply(_parse_length_mm),
            "Product Code": df[code_col].fillna("").astype(str).str.strip().str.upper(),
        }
    )

    out = out[out["Product Code"].str.match(r"^[A-Z0-9]{6,}$", na=False)]
    out = out[out["Particular"] != ""]
    return out


def export_product_output_format(input_path: Path, output_path: Path) -> Path:
    workbook = pd.ExcelFile(input_path)
    frames: list[pd.DataFrame] = []

    for sheet_name in workbook.sheet_names:
        df = pd.read_excel(input_path, sheet_name=sheet_name)
        normalized = {_normalize_col(col) for col in df.columns}
        needed = {"PRODUCTCODE", "PRODUCTNAME", "SIZE", "LENGTH"}
        if not needed.issubset(normalized):
            continue

        extracted = _extract_sheet(df)
        if not extracted.empty:
            frames.append(extracted)

    if not frames:
        raise ValueError("No sheets found with required columns PRODUCT CODE, PRODUCT NAME, SIZE, LENGTH")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["Product Code"], keep="first")

    combined["_len"] = pd.to_numeric(combined["Length(mm)"], errors="coerce")
    combined["_dia"] = pd.to_numeric(combined["Diameter Range"], errors="coerce")
    combined = combined.sort_values(by=["Particular", "_len", "_dia", "Product Code"], na_position="last")
    combined = combined.drop(columns=["_len", "_dia"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export all products in Particular/Diameter/Length/Product Code format")
    parser.add_argument(
        "--input",
        default="data/raw/master_list.xlsx",
        help="Input master workbook path",
    )
    parser.add_argument(
        "--output",
        default="data/processed/product_output_format.csv",
        help="Output csv path",
    )
    args = parser.parse_args()

    output_path = export_product_output_format(Path(args.input), Path(args.output))
    print(f"Exported: {output_path}")


if __name__ == "__main__":
    main()
