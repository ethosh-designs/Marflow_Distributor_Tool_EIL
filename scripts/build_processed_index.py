"""
build_processed_index.py
========================
Parses master_list.xlsx across all relevant sheets and produces
data/processed/processed_index.json

Each top-level key is a product family name (from index_docs.json).
Each family contains:
  - grammar_template: the index_docs.json template key
  - family_attributes: list of attribute columns actually present in this family
  - products: dict of product_code -> flat attribute dict (null for absent)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "raw" / "master_list.xlsx"
INDEX_DOCS_PATH = ROOT / "data" / "raw" / "index_docs.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "processed_index.json"

# ---------------------------------------------------------------------------
# Abbreviation master table
# ---------------------------------------------------------------------------
ABBREVIATIONS: dict[str, str] = {
    "BS":    "Braided Sheath",
    "NON-BS": "Non-Braided Sheath",
    "W/H":   "With Hole",
    "W/O-H": "Without Hole",
    "W/H-C": "With Hole Curved",
    "Ni":    "Nitinol",
    "NI":    "Nitinol",
    "PB":    "Polybraided",
    "GP":    "Green Pusher",
    "RP":    "Red Pusher",
    "BP":    "Blue Pusher",
    "BLP":   "Blue Pusher",
    "S":     "Scissor Type Handle",
    "F":     "Fish Type Handle",
    "D":     "D Type Handle",
    "NI-BT": "Nitinol Balloon",
    "NI-S":  "Nitinol Segura",
    "NI-XC": "Nitinol X-Circle",
    "NI-H":  "Nitinol Helical",
    "NI-GP": "Nitinol G-Paw",
    "PE":    "PEEK Sheath",
    "PT":    "PTFE Sheath",
    "PY":    "Polypropylene",
    "T":     "Tip Basket",
    "LP":    "Long Pusher",
    "HC":    "Hydrophilic Coating",
    "HGW":   "Hydrophilic Guidewire",
    "CE":    "Closed End",
    "OE":    "Open End",
    "BEO":   "Both End Open",
    "BEML":  "Both End Multi Loop",
    "SU":    "Suture",
    "CL":    "Clamp",
    "GW":    "Guidewire",
    "P":     "Premium",
    "N":     "Normal",
    "ST":    "Short Taper",
    "LT":    "Long Taper",
    "PU":    "Polyurethane",
    "SS":    "Stainless Steel",
    "SG":    "Stone Grasper",
    "Z":     "Tipless",
}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
_RE_FR    = re.compile(r"(\d+\.?\d*)\s*FR", re.IGNORECASE)
_RE_CM    = re.compile(r"(\d+\.?\d*)\s*CM", re.IGNORECASE)
_RE_MM    = re.compile(r"(\d+\.?\d*)\s*MM", re.IGNORECASE)
_RE_CH    = re.compile(r"(\d+)\s*CH", re.IGNORECASE)
_RE_WIRE  = re.compile(r"(\d)\s*WIRE", re.IGNORECASE)
_RE_BSIZE = re.compile(r"\b(07|09|10|12|15|17|18)\b")
_RE_BRACKET = re.compile(r"\(([^)]+)\)")
_RE_INNER_OUTER = re.compile(
    r"(\d+\.?\d*)\s*FR[./]*\s*/?\s*(\d+\.?\d*)", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Family detection: code-prefix → family name
# ---------------------------------------------------------------------------
PREFIX_TO_FAMILY: list[tuple[str, str]] = [
    ("MFUADS",   "AMPLATZ RENAL DILATOR SET"),
    ("MFUASD",   "AMPLATZ SHEATH WITH DILATOR"),
    ("MFUAD",    "AMPLATZ DILATOR"),
    ("MFUAS",    "AMPLATZ SHEATH"),
    ("MFUUAS",   "URETERAL ACCESS SHEATH"),
    ("MFUUC",    "URETERAL CATHETER"),
    ("MFUDJH",   "DOUBLE J STENT"),      # set variant
    ("MFUDJA",   "DOUBLE J STENT"),
    ("MFUDJC",   "DOUBLE J STENT"),
    ("MFUDJD",   "DOUBLE J STENT"),
    ("MFUDJI",   "DOUBLE J STENT"),
    ("MFUDJ",    "DOUBLE J STENT"),
    ("MFDJA",    "LONG LIFE DJ STENT"),
    ("MFDJC",    "LONG LIFE DJ STENT"),
    ("MFDJ",     "LONG LIFE DJ STENT"),
    ("MFUMJA",   "MONO J STENT CATHETER"),
    ("MFUMJ",    "MONO J STENT CATHETER"),
    ("MFUSB",    "STONE BASKET"),
    ("MFUGP",    "G-PAW BASKET"),
    ("MFUSG",    "STONE GRASPER"),
    ("MFUDLC",   "DUAL LUMEN URETERAL CATHETER"),
    ("BUDJA",    "DOUBLE J STENT"),
    ("BUDJC",    "DOUBLE J STENT"),
    ("BUDJD",    "DOUBLE J STENT"),
    ("BUDJI",    "DOUBLE J STENT"),
    ("BUDJ",     "DOUBLE J STENT"),
    ("BCCC",     "CYSTO CATHETER & SET"),
    ("BIBC",     "INTEGRAL BALLOON CATHETER"),
    ("BCBG",     "BIOPSY GUN"),
    ("BCCN",     "CHIBA NEEDLE"),
    ("BCIPN",    "INTRODUCER NEEDLE"),
    ("MFUES",    "ENDOPYELOTOMY STENT"),
    ("MFUFD",    "FILIFORM DILATOR"),
    ("BCFD",     "FASCIAL DILATOR"),
    ("BCGW",     "GUIDE WIRE"),
]

# Sub-brand text fragments → family (fallback if code prefix fails)
SUBBRAND_TO_FAMILY: list[tuple[str, str]] = [
    ("DJS BLUE",              "DOUBLE J STENT"),
    ("DJS WHITE",             "DOUBLE J STENT"),
    ("DJS BIOFLEX",           "DOUBLE J STENT"),
    ("DJS PRETOFLEX",         "DOUBLE J STENT"),
    ("DJS SET",               "DOUBLE J STENT"),
    ("DOUBLE J",              "DOUBLE J STENT"),
    ("LONG LIFE",             "LONG LIFE DJ STENT"),
    ("MONO J",                "MONO J STENT CATHETER"),
    ("URETERAL CATHETER",     "URETERAL CATHETER"),
    ("ACCESS SHEATH",         "URETERAL ACCESS SHEATH"),
    ("AMPLATZ RENAL DILATOR SET", "AMPLATZ RENAL DILATOR SET"),
    ("AMPLATZ DILATOR BLUE WITH SHEATH", "AMPLATZ SHEATH WITH DILATOR"),
    ("AMPLATZ DILATOR",       "AMPLATZ DILATOR"),
    ("AMPLATZ SHEATH",        "AMPLATZ SHEATH"),
    ("STONE BASKET",          "STONE BASKET"),
    ("G-PAW BASKET",          "G-PAW BASKET"),
    ("STONE GRASPER",         "STONE GRASPER"),
    ("DUAL LUMEN",            "DUAL LUMEN URETERAL CATHETER"),
    ("GUIDE WIRE",            "GUIDE WIRE"),
    ("CYSTO CATHETER",        "CYSTO CATHETER & SET"),
    ("BALLOON CATHETER",      "INTEGRAL BALLOON CATHETER"),
    ("BIOPSY GUN",            "BIOPSY GUN"),
    ("CHIBA NEEDLE",          "CHIBA NEEDLE"),
]

# ---------------------------------------------------------------------------
# Per-family attribute definitions
# Only these attributes will appear in the output for each family.
# ---------------------------------------------------------------------------
FAMILY_ATTRIBUTES: dict[str, list[str]] = {
    "DOUBLE J STENT": [
        "size_fr", "length_cm", "color", "end_type", "both_end_open",
        "pusher_type", "hydrophilic", "suture", "clamp",
        "guidewire", "guidewire_type", "variant_label", "material_type",
        "long_pusher",
    ],
    "LONG LIFE DJ STENT": [
        "size_fr", "length_cm", "color", "end_type", "both_end_open",
        "pusher_type", "hydrophilic", "suture", "clamp",
        "guidewire", "guidewire_type", "long_pusher", "material_type",
    ],
    "MONO J STENT CATHETER": [
        "size_fr", "length_cm", "color", "end_type",
        "pusher_type", "hydrophilic",
    ],
    "URETERAL CATHETER": [
        "size_fr", "length_cm", "color",
        "tip_type", "hydrophilic", "premium", "curved", "with_stylet",
    ],
    "AMPLATZ DILATOR": [
        "size_fr", "length_cm", "color", "taper", "hydrophilic",
    ],
    "AMPLATZ SHEATH WITH DILATOR": [
        "size_fr", "length_cm", "taper",
    ],
    "AMPLATZ RENAL DILATOR SET": [
        "size_fr_range", "length_cm", "taper", "hydrophilic", "num_sheaths", "color",
    ],
    "AMPLATZ SHEATH": [
        "outer_fr", "inner_fr", "length_cm",
    ],
    "STONE BASKET": [
        "size_fr", "num_wires", "length_cm",
        "basket_type", "handle_type", "sheath_material",
        "basket_size", "tip_type",
    ],
    "G-PAW BASKET": [
        "size_fr", "num_wires", "length_cm",
        "basket_type", "handle_type", "sheath_material", "basket_size",
    ],
    "STONE GRASPER": [
        "size_fr", "num_wires", "length_cm",
        "handle_type", "sheath_material", "basket_size",
    ],
    "URETERAL ACCESS SHEATH": [
        "inner_fr", "outer_fr", "length_cm", "braided_sheath", "hydrophilic",
    ],
    "DUAL LUMEN URETERAL CATHETER": [
        "size_fr", "length_cm", "color", "end_type", "premium", "hydrophilic",
    ],
    "CYSTO CATHETER & SET": [
        "size_fr", "length_cm", "catheter_type",
    ],
    "INTEGRAL BALLOON CATHETER": [
        "size_fr", "length_cm", "catheter_type",
    ],
    "GUIDE WIRE": [
        "size_mm", "length_cm", "guidewire_type", "hydrophilic",
    ],
    "BIOPSY GUN": [
        "size_fr", "length_cm",
    ],
    "CHIBA NEEDLE": [
        "size_fr", "length_cm",
    ],
    "INTRODUCER NEEDLE": [
        "size_fr", "length_cm",
    ],
    "ENDOPYELOTOMY STENT": [
        "size_fr", "length_cm",
    ],
    "FILIFORM DILATOR": [
        "size_fr", "length_cm",
    ],
    "FASCIAL DILATOR": [
        "size_fr", "length_cm", "hydrophilic",
    ],
}

# ---------------------------------------------------------------------------
# Helper: detect family from product code
# ---------------------------------------------------------------------------
def detect_family_from_code(code: str) -> str | None:
    code_upper = code.strip().upper()
    for prefix, family in PREFIX_TO_FAMILY:
        if code_upper.startswith(prefix.upper()):
            return family
    return None


def detect_family_from_subbrand(subbrand: str) -> str | None:
    sub_upper = str(subbrand).strip().upper()
    for fragment, family in SUBBRAND_TO_FAMILY:
        if fragment.upper() in sub_upper:
            return family
    return None


def detect_family(code: str, subbrand: str, description: str) -> str | None:
    family = detect_family_from_code(code)
    if family:
        return family
    family = detect_family_from_subbrand(subbrand)
    if family:
        return family
    # last-resort: scan description
    desc_upper = description.upper()
    for fragment, family in SUBBRAND_TO_FAMILY:
        if fragment.upper() in desc_upper:
            return family
    return None


# ---------------------------------------------------------------------------
# Helper: extract bracket tokens
# ---------------------------------------------------------------------------
def _bracket_tokens(desc: str) -> list[str]:
    """Return tokens extracted from all (…) groups, split on '-'."""
    tokens: list[str] = []
    for group in _RE_BRACKET.findall(desc):
        for part in group.split("-"):
            t = part.strip().upper()
            if t:
                tokens.append(t)
    return tokens


def _all_tokens(desc: str) -> set[str]:
    """All whitespace-split tokens from the full description."""
    return {t.strip().upper() for t in re.split(r"[\s,./]+", desc) if t.strip()}


# ---------------------------------------------------------------------------
# Attribute parsers
# ---------------------------------------------------------------------------

def _parse_fr(desc: str) -> float | None:
    m = _RE_FR.search(desc)
    return float(m.group(1)) if m else None


def _parse_cm(desc: str) -> float | None:
    m = _RE_CM.search(desc)
    return float(m.group(1)) if m else None


def _parse_mm(desc: str) -> float | None:
    m = _RE_MM.search(desc)
    return float(m.group(1)) if m else None


def _parse_color(tokens: set[str]) -> str | None:
    for c in ("BLUE", "GREEN", "WHITE", "YELLOW", "BLACK"):
        if c in tokens:
            return c
    return None


def _parse_end_type(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    # BEO takes priority over CE/OE
    if "BEO" in all_t:
        return "BEO"
    if "CE" in all_t or "CLOSED" in all_t:
        return "CE"
    if "OE" in all_t or ("OPEN" in all_t and "END" in all_t):
        return "OE"
    return None


def _parse_pusher(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    if "GP" in all_t:
        return "GP"
    if "BLP" in all_t or "BP" in all_t:
        return "BLP"
    if "RP" in all_t:
        return "RP"
    return None


def _parse_hydrophilic(br_tokens: list[str], desc_tokens: set[str], desc: str) -> bool | None:
    all_t = set(br_tokens) | desc_tokens
    if "HYDROPHILIC" in all_t or "HC" in all_t or "HGW" in all_t:
        return True
    if "WITH HYDROPHILIC" in desc.upper() or "HYDROPHILIC COATING" in desc.upper():
        return True
    return None


def _parse_tip_type(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    desc_joined = " ".join(br_tokens + list(desc_tokens))

    if "TIEMAN" in all_t:
        return "Tieman"
    if "OLIVE TIP" in desc_joined or ("OLIVE" in all_t and "TIP" in all_t):
        return "Olive Tip"
    if "BULB TIP" in desc_joined or ("BULB" in all_t and "TIP" in all_t):
        return "Bulb Tip"
    if "CONE TIP" in desc_joined or ("CONE" in all_t and "TIP" in all_t):
        return "Cone Tip"
    if "PIGTAIL TIP" in desc_joined or "PIGTAIL" in all_t:
        return "Pigtail Tip"
    if "WHISTLE TIP" in desc_joined or "WHISTLE" in all_t:
        return "Whistle Tip"
    if "SPIRAL TIP" in desc_joined or "SPIRAL" in all_t:
        return "Spiral Tip"
    if "OPEN END" in desc_joined or "OPEN-END" in desc_joined or "OE" in all_t:
        return "Open End"
    if "CLOSE END" in desc_joined or "CLOSED END" in desc_joined:
        return "Close End"
    return None


def _parse_taper(br_tokens: list[str], desc_tokens: set[str], desc: str) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    desc_up = desc.upper()
    if "SHORT TAPER" in desc_up or "ST" in all_t:
        return "Short Taper"
    if "LONG TAPER" in desc_up or "LT" in all_t or "LIGHT BLUE WITH LONG TAPER" in desc_up:
        return "Long Taper"
    return None


def _parse_basket_type(br_tokens: list[str]) -> str | None:
    for t in br_tokens:
        if t in ("NI-S", "NI-BT", "NI-XC", "NI-H", "NI-GP"):
            return ABBREVIATIONS.get(t, t)
    return None


def _parse_handle_type(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    # Scan bracket tokens for S/F/D handle codes
    # but avoid false positives - only positions 2 or 3 in basket brackets
    # We'll scan all bracket tokens for isolated S, F, D
    for t in br_tokens:
        if t == "S":
            return "Scissor"
        if t == "F":
            return "Fish"
        if t == "D":
            return "D-shape"
    return None


def _parse_sheath_material(br_tokens: list[str]) -> str | None:
    for t in br_tokens:
        if t == "PE":
            return "PEEK"
        if t == "PT":
            return "PTFE"
        if t == "PB":
            return "Polybraided"
        if t == "PY":
            return "Polypropylene"
    return None


def _parse_basket_size(br_tokens: list[str]) -> str | None:
    for t in br_tokens:
        m = _RE_BSIZE.fullmatch(t)
        if m:
            return m.group(1)
    return None


def _parse_tip_basket(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    if "T" in all_t:
        # Only treat as Tip Basket when combined with basket bracket context
        for t in br_tokens:
            if t == "T":
                return "Tip"
    # Check for ZERO TIP
    joined = " ".join(br_tokens)
    if "ZERO TIP" in joined or "Z" in set(br_tokens):
        return "Zero Tip"
    return None


def _parse_num_wires(desc: str) -> int | None:
    m = _RE_WIRE.search(desc)
    return int(m.group(1)) if m else None


def _parse_variant_label(desc: str) -> str | None:
    """Extract parenthesised variant label from DJ stent descriptions."""
    m = _RE_BRACKET.search(desc)
    if m:
        return m.group(1).strip()
    return None


def _parse_material_type(desc: str, br_tokens: list[str]) -> str | None:
    desc_up = desc.upper()
    if "BIOFLEX" in desc_up:
        return "Bioflex"
    if "PRETOFLEX" in desc_up:
        return "Pretoflex"
    if "LONG LIFE" in desc_up or "360D" in desc_up:
        return "Long Life 360D"
    all_t = set(br_tokens)
    if "PU" in all_t:
        return "Polyurethane"
    return None


def _parse_inner_outer_fr(desc: str) -> tuple[float | None, float | None]:
    """For access sheaths: extract inner/outer FR from descriptions like 09.5FR/11.5."""
    m = _RE_INNER_OUTER.search(desc)
    if m:
        return float(m.group(1)), float(m.group(2))
    # fallback: look for (ID X FR - OD Y FR) pattern
    id_m = re.search(r"ID\s*(\d+\.?\d*)\s*FR", desc, re.IGNORECASE)
    od_m = re.search(r"OD\s*(\d+\.?\d*)\s*FR", desc, re.IGNORECASE)
    if id_m and od_m:
        return float(id_m.group(1)), float(od_m.group(1))
    return None, None


def _parse_guidewire_type(br_tokens: list[str], desc_tokens: set[str]) -> str | None:
    all_t = set(br_tokens) | desc_tokens
    if "HGW" in all_t or "HYDROPHILIC" in all_t:
        return "Hydrophilic"
    if "COBRA" in all_t:
        return "Cobra"
    if "PTFE" in all_t:
        return "PTFE"
    if "GW" in all_t or "GUIDEWIRE" in all_t:
        return "Standard"
    return None


def _parse_braided_sheath(br_tokens: list[str], desc: str) -> str | None:
    joined = " ".join(br_tokens).upper()
    desc_up = desc.upper()
    if "NON-BS" in joined or "NON-BS" in desc_up:
        return "Non-Braided"
    if "BS" in set(br_tokens) or "BRAIDED" in desc_up:
        return "Braided"
    return None


def _parse_catheter_type(br_tokens: list[str], desc: str) -> str | None:
    desc_up = desc.upper()
    if "2-WAY" in desc_up or "2 WAY" in desc_up:
        return "2-Way"
    if "3-WAY" in desc_up or "3 WAY" in desc_up:
        return "3-Way"
    return None


def _parse_num_sheaths(desc: str) -> int | None:
    m = re.search(r"(\d)\s*SHEATH", desc, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_size_fr_range(desc: str) -> str | None:
    m = re.search(r"(\d+)\s*-\s*(\d+)\s*FR", desc, re.IGNORECASE)
    return f"{m.group(1)}-{m.group(2)} FR" if m else None


# ---------------------------------------------------------------------------
# Master attribute extractor
# ---------------------------------------------------------------------------

def extract_attributes(
    product_code: str,
    description: str,
    family: str,
) -> dict[str, Any]:
    desc = str(description).strip()
    br_tokens = _bracket_tokens(desc)
    desc_tokens = _all_tokens(desc)
    all_t = set(br_tokens) | desc_tokens
    attrs: dict[str, Any] = {}

    # --- Universal ---
    attrs["size_fr"] = _parse_fr(desc)
    attrs["length_cm"] = _parse_cm(desc)
    attrs["color"] = _parse_color(desc_tokens)

    # --- End type & pusher ---
    attrs["end_type"] = _parse_end_type(br_tokens, desc_tokens)
    attrs["both_end_open"] = True if "BEO" in all_t else None
    attrs["pusher_type"] = _parse_pusher(br_tokens, desc_tokens)
    attrs["long_pusher"] = True if ("LP" in all_t or "WITH LONG PUSHER" in desc.upper() or "LONG PUSHER" in desc.upper()) else None

    # --- Hydrophilic ---
    attrs["hydrophilic"] = _parse_hydrophilic(br_tokens, desc_tokens, desc)

    # --- Accessories ---
    attrs["suture"] = True if "SU" in all_t else None
    attrs["clamp"] = True if "CL" in all_t else None
    attrs["guidewire"] = True if ("GW" in all_t or "HGW" in all_t or "GUIDEWIRE" in desc.upper()) else None
    attrs["guidewire_type"] = _parse_guidewire_type(br_tokens, desc_tokens)

    # --- Material / variant ---
    attrs["variant_label"] = _parse_variant_label(desc)
    attrs["material_type"] = _parse_material_type(desc, br_tokens)

    # --- Ureteral catheter ---
    attrs["tip_type"] = _parse_tip_type(br_tokens, desc_tokens)
    attrs["premium"] = True if ("PREMIUM" in all_t or "P" in set(br_tokens)) else None
    attrs["curved"] = True if "CURVED" in all_t else None
    attrs["with_stylet"] = True if "STYLET" in all_t else None

    # --- Amplatz ---
    attrs["taper"] = _parse_taper(br_tokens, desc_tokens, desc)
    attrs["size_fr_range"] = _parse_size_fr_range(desc)
    attrs["num_sheaths"] = _parse_num_sheaths(desc)

    # --- Access sheath ---
    inner, outer = _parse_inner_outer_fr(desc)
    attrs["inner_fr"] = inner
    attrs["outer_fr"] = outer
    attrs["braided_sheath"] = _parse_braided_sheath(br_tokens, desc)

    # --- Baskets ---
    attrs["num_wires"] = _parse_num_wires(desc)
    attrs["basket_type"] = _parse_basket_type(br_tokens)
    attrs["handle_type"] = _parse_handle_type(br_tokens, desc_tokens)
    attrs["sheath_material"] = _parse_sheath_material(br_tokens)
    attrs["basket_size"] = _parse_basket_size(br_tokens)
    attrs["tip_type_basket"] = _parse_tip_basket(br_tokens, desc_tokens)

    # --- Guide wire ---
    attrs["size_mm"] = _parse_mm(desc)

    # --- Cysto ---
    attrs["catheter_type"] = _parse_catheter_type(br_tokens, desc)

    return attrs


# ---------------------------------------------------------------------------
# Load sheets from master_list.xlsx
# ---------------------------------------------------------------------------

_SHEET_COL_MAP = {
    # sheet_name: (code_col_name_fragment, desc_col_name_fragment, subbrand_col_fragment)
    "URO Product Code list .": ("PRODUCT CODE", "PRODUCT DESCRIPTION", "PRODUCT SUB BRAND"),
    "Custmized P-Codes":       ("PRODUCT CODE", "PRODUCT DESCRIPTION", "PRODUCT SUB BRAND"),
    "MF_Codes":                ("PRODUCT CODE", "PRODUCT DESCRIPTION", "PRODUCT SUB BRAND"),
}


def _find_col(columns: list[str], fragment: str) -> int | None:
    frag_up = fragment.upper()
    for i, c in enumerate(columns):
        if frag_up in str(c).upper():
            return i
    return None


def load_master_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    xl = pd.ExcelFile(MASTER_PATH)
    for sheet_name, (code_frag, desc_frag, sub_frag) in _SHEET_COL_MAP.items():
        if sheet_name not in xl.sheet_names:
            print(f"  [WARN] sheet '{sheet_name}' not found, skipping")
            continue

        df = pd.read_excel(xl, sheet_name=sheet_name, header=0)
        # Columns are auto-numbered; find by searching header row text
        raw_cols = list(df.columns)
        col_code = _find_col(raw_cols, code_frag)
        col_desc = _find_col(raw_cols, desc_frag)
        col_sub  = _find_col(raw_cols, sub_frag)

        if col_code is None or col_desc is None:
            print(f"  [WARN] could not find code/desc columns in '{sheet_name}'")
            continue

        for _, row in df.iterrows():
            code = str(row.iloc[col_code]).strip()
            desc = str(row.iloc[col_desc]).strip()
            sub  = str(row.iloc[col_sub]).strip() if col_sub is not None else ""

            # Skip blank / header rows
            if not code or code.lower() in {"nan", "product code", "art code"}:
                continue
            if not desc or desc.lower() == "nan":
                continue
            # Skip rows that aren't product codes (no alpha prefix)
            if not re.match(r"[A-Za-z]", code):
                continue
            # Deduplicate by product code
            if code in seen:
                continue
            seen.add(code)
            rows.append({"product_code": code, "product_description": desc, "subbrand": sub})

    return rows


# ---------------------------------------------------------------------------
# Build processed index
# ---------------------------------------------------------------------------

def build_index() -> dict[str, Any]:
    print("Loading index_docs.json …")
    with open(INDEX_DOCS_PATH, encoding="utf-8") as f:
        index_docs: dict[str, Any] = json.load(f)

    # Build template → family name lookup
    template_to_family: dict[str, str] = {
        tmpl: info["name"] for tmpl, info in index_docs.items()
    }

    print("Loading master_list.xlsx …")
    rows = load_master_rows()
    print(f"  Loaded {len(rows)} unique product rows")

    # Group rows by family
    family_rows: dict[str, list[dict[str, str]]] = {}
    skipped = 0
    for row in rows:
        family = detect_family(row["product_code"], row["subbrand"], row["product_description"])
        if family is None:
            skipped += 1
            continue
        family_rows.setdefault(family, []).append(row)

    print(f"  Detected {len(family_rows)} families, skipped {skipped} unrecognised rows")

    # Build output structure
    output: dict[str, Any] = {}

    # Resolve grammar template for each family
    family_to_template: dict[str, str] = {}
    for tmpl, info in index_docs.items():
        family_to_template[info["name"]] = tmpl

    for family, items in sorted(family_rows.items()):
        wanted_attrs = FAMILY_ATTRIBUTES.get(family)
        if wanted_attrs is None:
            # Generic fallback — use common attributes
            wanted_attrs = ["size_fr", "length_cm", "color", "hydrophilic"]

        products_dict: dict[str, Any] = {}
        # Track which attrs are actually populated in this family
        populated: set[str] = set()

        for item in items:
            code = item["product_code"]
            desc = item["product_description"]
            raw_attrs = extract_attributes(code, desc, family)

            # Build product entry with only family-relevant attrs
            product_entry: dict[str, Any] = {
                "product_code": code,
                "product_description": desc,
            }
            for attr in wanted_attrs:
                val = raw_attrs.get(attr)
                product_entry[attr] = val
                if val is not None:
                    populated.add(attr)

            products_dict[code] = product_entry

        # Trim: only include attrs actually used in this family
        used_attrs = [a for a in wanted_attrs if a in populated]

        output[family] = {
            "grammar_template": family_to_template.get(family, None),
            "family_attributes": used_attrs,
            "product_count": len(products_dict),
            "products": products_dict,
        }
        print(f"  [{family}]  {len(products_dict)} products  attrs={used_attrs}")

    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = build_index()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    total_products = sum(v["product_count"] for v in result.values())
    print(f"\nDone. {len(result)} families, {total_products} products -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
