"""
build_new_index_doc.py
======================
Produces data/processed/new_index_doc.json

Starts from data/raw/index_docs.json (exact copy of every template / segment /
variants entry) and adds an "attributes" block to each template.

The "attributes" block is derived by:
  1. Scanning every matching product description in master_list.xlsx
  2. Parsing bracket tokens (NI-H-F-PE-09-T, CE-GP-SU-CL, OPEN END-PREMIUM, …)
  3. Mapping tokens to structured attribute dimensions using the abbreviation table
     supplied by the domain team

Run:
    python scripts/build_new_index_doc.py
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT          = Path(__file__).resolve().parents[1]
INDEX_IN      = ROOT / "data" / "raw"   / "index_docs.json"
MASTER_PATH   = ROOT / "data" / "raw"   / "master_list.xlsx"
OUTPUT_PATH   = ROOT / "data" / "processed" / "new_index_doc.json"

# ---------------------------------------------------------------------------
# Full abbreviation / expansion table (domain-supplied + extended)
# ---------------------------------------------------------------------------
ABBR: dict[str, str] = {
    # End types
    "CE":      "Closed End",
    "OE":      "Open End",
    "BEO":     "Both End Open",
    "BEML":    "Both End Multi Loop",
    "OEML":    "One End Multi Loop",
    # Pushers
    "GP":      "Green Pusher",
    "RP":      "Red Pusher",
    "BP":      "Blue/Brown Pusher",
    "BLP":     "Blue Pusher",
    # Accessories
    "SU":      "Suture",
    "CL":      "Clamp",
    "GW":      "Guidewire",
    "HGW":     "Hydrophilic Guidewire",
    "HC":      "Hydrophilic Coating",
    "LP":      "Long Pusher",
    # Wire / basket types
    "NI":      "Nitinol",
    "NI-S":    "Nitinol Segura",
    "NI-H":    "Nitinol Helical",
    "NI-BT":   "Nitinol Balloon",
    "NI-XC":   "Nitinol X-Circle",
    "NI-GP":   "Nitinol G-Paw",
    "Z":       "Tipless (Zero Tip)",
    "T":       "Tip Basket",
    "ZERO TIP":"Tipless (Zero Tip)",
    # Handles
    "S":       "Scissor Type Handle",
    "F":       "Fish Type Handle",
    "D":       "D Type Handle",
    # Sheath materials
    "PE":      "PEEK Sheath",
    "PT":      "PTFE Sheath",
    "PB":      "Polybraided",
    "PY":      "Polypropylene",
    "BS":      "Braided Sheath",
    "NON-BS":  "Non-Braided Sheath",
    # Access sheath models
    "UROX-F":  "UROX-F Flexible Suction",
    "UROX-FC": "UROX-FC Flexible Suction with Channel",
    # Catheter tips
    "OPEN END":        "Open End",
    "CLOSE END":       "Close End",
    "CLOSED END":      "Close End",
    "CONE TIP":        "Cone Tip",
    "BULB TIP":        "Bulb Tip",
    "TIEMAN":          "Tieman Tip",
    "OLIVE TIP":       "Olive Tip",
    "PIGTAIL TIP":     "Pigtail Tip",
    "SPIRAL TIP":      "Spiral Tip",
    "WHISTLE TIP":     "Whistle Tip",
    # Grade
    "P":       "Premium",
    "N":       "Normal",
    # Taper
    "LT":      "Long Taper",
    "ST":      "Short Taper",
    # Stone grasper
    "SG":      "Stone Grasper",
    "SS":      "Stainless Steel",
    # Material
    "PU":      "Polyurethane",
    "W/H":     "With Hole",
    "W/O-H":   "Without Hole",
    "W/H-C":   "With Hole Curved",
}

# ---------------------------------------------------------------------------
# Which sheets to scan and which columns hold code / description
# ---------------------------------------------------------------------------
SHEETS = {
    "MF_Codes":                  (13, 14),
    "URO Product Code list .":   (12, 13),
    "Custmized P-Codes":         (13, 14),
}

_BRACKET_RE = re.compile(r"\(([^)]+)\)")


logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Load all product rows from master (code, description)
# ---------------------------------------------------------------------------
def _load_master() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    xl = pd.ExcelFile(MASTER_PATH)
    for sheet, (ci, di) in tqdm(SHEETS.items(), desc="Scanning master sheets", unit="sheet"):
        if sheet not in xl.sheet_names:
            logger.warning("Sheet '%s' not found in master workbook; skipping.", sheet)
            continue
        df = pd.read_excel(xl, sheet_name=sheet, header=0)
        df.columns = range(len(df.columns))
        codes = df[ci].fillna("").astype(str).str.strip()
        descs = df[di].fillna("").astype(str).str.strip()
        for code, desc in zip(codes, descs):
            if not code or not re.match(r"[A-Za-z]", code):
                continue
            if code in seen:
                continue
            seen.add(code)
            rows.append((code.upper(), desc))
    return rows


# ---------------------------------------------------------------------------
# Bracket → token list  (splits on "-" but keeps compound tokens like NI-S)
# ---------------------------------------------------------------------------
_COMPOUND = {
    "NI-S", "NI-H", "NI-BT", "NI-XC", "NI-GP",
    "W/H", "W/O-H", "W/H-C", "NON-BS",
    "ZERO TIP",
    "UROX-F", "UROX-FC",
    "SG-SS",
}

def _parse_bracket(text: str) -> list[str]:
    """Split 'NI-H-F-PT-09-ZERO TIP' → ['NI-H', 'F', 'PT', '09', 'ZERO TIP']"""
    text = text.strip()
    tokens: list[str] = []
    remaining = text.upper()

    # Greedily match known compound tokens first
    ordered = sorted(_COMPOUND, key=len, reverse=True)
    while remaining:
        matched = None
        for comp in ordered:
            if remaining.startswith(comp):
                tokens.append(comp)
                remaining = remaining[len(comp):]
                remaining = remaining.lstrip("-").lstrip()
                matched = True
                break
        if not matched:
            # Take next dash-delimited chunk
            if "-" in remaining:
                chunk, remaining = remaining.split("-", 1)
                remaining = remaining.lstrip()
            else:
                chunk = remaining
                remaining = ""
            if chunk.strip():
                tokens.append(chunk.strip())

    return tokens


def _bracket_tokens_for_desc(desc: str) -> list[list[str]]:
    """Return one token-list per bracket group found in desc."""
    groups = []
    for match in _BRACKET_RE.finditer(desc):
        raw = match.group(1).strip()
        groups.append(_parse_bracket(raw))
    return groups


# ---------------------------------------------------------------------------
# Collect all bracket token-sets for products whose code starts with any prefix
# ---------------------------------------------------------------------------
def _collect_brackets(
    master_rows: list[tuple[str, str]],
    prefixes: list[str],
) -> list[list[str]]:
    all_groups: list[list[str]] = []
    for code, desc in master_rows:
        if any(code.startswith(p.upper()) for p in prefixes):
            all_groups.extend(_bracket_tokens_for_desc(desc))
    return all_groups


def _unique_values(groups: list[list[str]], position: int | None = None) -> list[str]:
    """Collect unique values at a given position (None = all positions)."""
    vals: set[str] = set()
    for grp in groups:
        if position is None:
            vals.update(grp)
        elif position < len(grp):
            vals.add(grp[position])
    return sorted(vals)


def _expand(token: str) -> str:
    return ABBR.get(token, token)


# ---------------------------------------------------------------------------
# Attribute builder helpers
# ---------------------------------------------------------------------------
def _options_dict(tokens: list[str]) -> dict[str, str]:
    return {t: _expand(t) for t in tokens if t}


def _attr(description: str, options: dict[str, str] | list[str]) -> dict:
    if isinstance(options, list):
        options = {v: _expand(v) for v in options}
    return {"description": description, "options": options}


# ---------------------------------------------------------------------------
# Per-family attribute builders
# Each builder receives the raw bracket groups collected from master data
# and returns the "attributes" dict to embed in the template entry.
# ---------------------------------------------------------------------------

def _attrs_dj(groups: list[list[str]]) -> dict:
    """Double J Stent / Long Life DJ Stent"""
    end_types   = _unique_values(groups, 0)
    loop_types  = sorted({t for g in groups for t in g if t in ("OEML","BEML")})
    pushers     = sorted({t for g in groups for t in g if t in ("GP","RP","BP","BLP")})
    accessories = sorted({t for g in groups for t in g if t in ("SU","CL","GW","HGW")})

    return {
        "end_configuration": _attr(
            "End type of the stent",
            {t: _expand(t) for t in end_types if t in ABBR}
        ),
        "loop_type": _attr(
            "Multi-loop configuration",
            dict(standard="Standard (no extra loop)", **{t: _expand(t) for t in loop_types})
        ),
        "pusher_type": _attr(
            "Pusher included in set",
            _options_dict(pushers)
        ),
        "accessories": _attr(
            "Optional accessories included",
            _options_dict(accessories)
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating on stent surface",
            {"yes": "With Hydrophilic Coating", "no": "Without Hydrophilic Coating"}
        ),
        "long_pusher": _attr(
            "Extended pusher length",
            {"yes": "With Long Pusher", "no": "Standard Pusher"}
        ),
    }


def _attrs_mj(groups: list[list[str]]) -> dict:
    """Mono J Stent Catheter"""
    pushers     = sorted({t for g in groups for t in g if t in ("GP","RP","BP","BLP")})
    accessories = sorted({t for g in groups for t in g if t in ("CL","GW","HGW")})
    end_types   = _unique_values(groups, 0)

    return {
        "end_configuration": _attr(
            "End type of the stent",
            {t: _expand(t) for t in end_types if t in ABBR}
        ),
        "pusher_type": _attr(
            "Pusher included",
            _options_dict(pushers)
        ),
        "accessories": _attr(
            "Optional accessories",
            _options_dict(accessories)
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating",
            {"yes": "With Hydrophilic Coating", "no": "Without Hydrophilic Coating"}
        ),
    }


def _attrs_stone_basket(groups: list[list[str]]) -> dict:
    """
    Stone Basket bracket format: NI-{TYPE}-{HANDLE}-{SHEATH}-{SIZE}-{TIP}
    e.g. NI-H-F-PE-09-T  or  NI-BT-D-PT-12-ZERO TIP
    """
    wire_types    = sorted({g[0] for g in groups if g and g[0] in ("NI-S","NI-H","NI-BT","NI-XC")})
    handles       = sorted({t for g in groups for t in g if t in ("S","F","D")})
    sheaths       = sorted({t for g in groups for t in g if t in ("PE","PT","PB","PY")})
    sizes         = sorted({t for g in groups for t in g
                            if re.fullmatch(r"\d{2}", t)})
    tip_values    = sorted({t for g in groups for t in g
                            if t in ("T","Z","ZERO TIP")})

    return {
        "basket_subtype": _attr(
            "Stone basket wire configuration / shape family",
            {
                "NI-S":  "Segura Basket (Nitinol)",
                "NI-H":  "Helical Basket (Nitinol)",
                "NI-BT": "Balloon Basket (Nitinol)",
                "NI-XC": "X-Circle Basket (Nitinol)",
            }
        ),
        "tip_configuration": _attr(
            "Tip vs Tipless (Zero Tip) configuration",
            {
                "T":        "Tip Basket",
                "ZERO TIP": "Tipless / Zero Tip Basket",
                "Z":        "Tipless / Zero Tip Basket",
            }
        ),
        "handle_type": _attr(
            "Handle design",
            {
                "S": "Scissor Type Handle",
                "F": "Fish Type Handle",
                "D": "D Type Handle",
            }
        ),
        "sheath_material": _attr(
            "Sheath material",
            {
                "PE": "PEEK Sheath",
                "PT": "PTFE Sheath",
                "PB": "Polybraided",
                "PY": "Polypropylene",
            }
        ),
        "basket_size_mm": _attr(
            "Basket opening diameter (mm)",
            {s: f"{int(s)} mm" for s in ["09","12","15","17"]}
        ),
    }


def _attrs_gpaw(groups: list[list[str]]) -> dict:
    """
    G-Paw Basket bracket format: NI-GP-{HANDLE}-{SHEATH}-{SIZE}
    """
    handles = sorted({t for g in groups for t in g if t in ("S","F","D")})
    sheaths = sorted({t for g in groups for t in g if t in ("PE","PT","PB","PY")})
    sizes   = sorted({t for g in groups for t in g if re.fullmatch(r"\d{2}", t)})

    return {
        "wire_type": _attr(
            "Wire material and design",
            {"NI-GP": "Nitinol G-Paw"}
        ),
        "handle_type": _attr(
            "Handle design",
            _options_dict(handles)
        ),
        "sheath_material": _attr(
            "Sheath material",
            _options_dict(sheaths)
        ),
        "basket_size_mm": _attr(
            "Basket opening diameter (mm)",
            {s: f"{int(s)} mm" for s in sizes if s}
        ),
    }


def _attrs_stone_grasper(groups: list[list[str]]) -> dict:
    """
    Stone Grasper bracket format: SG-SS-{HANDLE}-{SHEATH}-{SIZE}
    """
    handles = sorted({t for g in groups for t in g if t in ("S","F","D")})
    sheaths = sorted({t for g in groups for t in g if t in ("PE","PT","PB","PY")})
    sizes   = sorted({t for g in groups for t in g if re.fullmatch(r"\d{2}", t)})

    return {
        "type": _attr(
            "Grasper material",
            {"SG-SS": "Stainless Steel Stone Grasper"}
        ),
        "handle_type": _attr(
            "Handle design",
            _options_dict(handles)
        ),
        "sheath_material": _attr(
            "Sheath material",
            _options_dict(sheaths)
        ),
        "basket_size_mm": _attr(
            "Grasper opening diameter (mm)",
            {s: f"{int(s)} mm" for s in sizes if s}
        ),
    }


def _attrs_ureteral_catheter(groups: list[list[str]]) -> dict:
    """
    Ureteral Catheter bracket: {TIP_TYPE}-{GRADE}
    e.g. OPEN END-PREMIUM, TIEMAN-CLOSE END-PREMIUM
    """
    tips = sorted({
        t for g in groups for t in g
        if t in (
            "OPEN END","CLOSE END","CLOSED END",
            "CONE TIP","BULB TIP","TIEMAN","OLIVE TIP",
            "PIGTAIL TIP","SPIRAL TIP","WHISTLE TIP",
        )
    })
    grades = sorted({t for g in groups for t in g if t in ("P","N","PREMIUM","NORMAL")})

    tip_options = {}
    for t in [
        "OPEN END","CLOSE END","CONE TIP","BULB TIP",
        "TIEMAN","OLIVE TIP","PIGTAIL TIP","SPIRAL TIP","WHISTLE TIP"
    ]:
        tip_options[t] = _expand(t)

    return {
        "tip_type": _attr(
            "Catheter tip design",
            tip_options
        ),
        "tieman_end": _attr(
            "Tieman tip end configuration (only when tip_type is TIEMAN)",
            {
                "OPEN END":  "Tieman with Open End",
                "CLOSE END": "Tieman with Close End",
            }
        ),
        "grade": _attr(
            "Product grade / quality tier",
            {
                "P": "Premium",
                "N": "Normal",
            }
        ),
        "accessories": _attr(
            "Included accessories",
            {
                "WITH STYLET":        "With Stylet",
                "HYDROPHILIC COATED": "Hydrophilic Coated Surface",
            }
        ),
    }


def _attrs_access_sheath(groups: list[list[str]]) -> dict:
    """
    Access Sheath brackets: (BS|NON-BS) … (UROX-F|UROX-FC)
    """
    sheath_types = sorted({t for g in groups for t in g if t in ("BS","NON-BS","BA","BRAIDED SHAFT","NON-BRAIDED SHAFT")})
    models       = sorted({t for g in groups for t in g if t in ("UROX-F","UROX-FC")})

    return {
        "sheath_construction": _attr(
            "Shaft / sheath construction type",
            {
                "BS":    "Braided Sheath",
                "NON-BS":"Non-Braided Sheath",
            }
        ),
        "model_series": _attr(
            "Product model / series",
            {
                "UROX-F":  "UROX-F Flexible Suction Access Sheath",
                "UROX-FC": "UROX-FC Flexible Suction Access Sheath with Channel",
            }
        ),
        "inner_outer_fr": _attr(
            "Lumen sizes (Inner FR / Outer FR)",
            {
                "8.5/10.5":  "8.5 FR inner / 10.5 FR outer",
                "9.5/11.5":  "9.5 FR inner / 11.5 FR outer",
                "10.0/12.0": "10.0 FR inner / 12.0 FR outer",
                "11.0/13.0": "11.0 FR inner / 13.0 FR outer",
                "12.0/14.0": "12.0 FR inner / 14.0 FR outer",
                "13.0/15.0": "13.0 FR inner / 15.0 FR outer",
                "14.0/16.0": "14.0 FR inner / 16.0 FR outer",
            }
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating",
            {"yes": "With Hydrophilic Coating", "no": "Without Hydrophilic Coating"}
        ),
    }


def _attrs_amplatz_dilator(_groups: list[list[str]]) -> dict:
    return {
        "taper_type": _attr(
            "Distal taper profile",
            {
                "LT": "Long Taper",
                "ST": "Short Taper",
            }
        ),
        "color": _attr(
            "Dilator colour",
            {"BLUE": "Blue"}
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating option",
            {"yes": "With Hydrophilic Coating", "no": "Without"}
        ),
    }


def _attrs_amplatz_sheath_dil(_groups: list[list[str]]) -> dict:
    return {
        "taper_type": _attr(
            "Distal taper profile",
            {"LT": "Long Taper", "ST": "Short Taper"}
        ),
        "color": _attr(
            "Sheath / dilator colour",
            {"BLUE": "Blue"}
        ),
    }


def _attrs_amplatz_set(groups: list[list[str]]) -> dict:
    return {
        "taper_type": _attr(
            "Dilator taper profile",
            {"LT": "Long Taper", "ST": "Short Taper"}
        ),
        "color_variant": _attr(
            "Colour variant of dilators in set",
            {
                "BLUE":       "Standard Blue",
                "LIGHT BLUE": "Light Blue",
            }
        ),
        "num_sheaths": _attr(
            "Number of sheaths included in set",
            {
                "1": "Single Sheath",
                "2": "Two Sheaths",
            }
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating",
            {"yes": "With Hydrophilic Coating", "no": "Without"}
        ),
    }


def _attrs_amplatz_sheath(_groups: list[list[str]]) -> dict:
    return {
        "lumen_configuration": _attr(
            "Inner / Outer diameter pair (FR)",
            {
                "12/16": "ID 12 FR – OD 16 FR",
                "14/18": "ID 14 FR – OD 18 FR",
                "16/20": "ID 16 FR – OD 20 FR",
                "18/22": "ID 18 FR – OD 22 FR",
                "20/24": "ID 20 FR – OD 24 FR",
                "22/26": "ID 22 FR – OD 26 FR",
                "24/28": "ID 24 FR – OD 28 FR",
                "26/30": "ID 26 FR – OD 30 FR",
                "28/32": "ID 28 FR – OD 32 FR",
                "30/34": "ID 30 FR – OD 34 FR",
                "32/36": "ID 32 FR – OD 36 FR",
                "34/38": "ID 34 FR – OD 38 FR",
            }
        ),
    }


def _attrs_dual_lumen(_groups: list[list[str]]) -> dict:
    return {
        "end_type": _attr(
            "End configuration",
            {"OE": "Open End"}
        ),
        "grade": _attr(
            "Grade",
            {"P": "Premium"}
        ),
        "color": _attr(
            "Colour",
            {"YELLOW": "Yellow"}
        ),
        "hydrophilic_coating": _attr(
            "Hydrophilic coating",
            {"yes": "With Hydrophilic Coating", "no": "Without"}
        ),
    }


def _attrs_generic() -> dict:
    return {}


# ---------------------------------------------------------------------------
# Map each index_docs template → (code prefixes to scan, builder function)
# ---------------------------------------------------------------------------
TEMPLATE_MAP: dict[str, tuple[list[str], callable]] = {
    "MFUDJV00DDLLHX":  (["MFUDJA","MFUDJC","MFUDJD","MFUDJI","MFUDJH",
                          "BUDJA","BUDJC","BUDJD","BUDJI"],       _attrs_dj),
    "MFUMJV0DDLLHX":   (["MFUMJA","MFUMJC","MFUMJD","BUMJA","BUMJC"],  _attrs_mj),
    "MFUADXXDDLLH":    (["MFUAD0"],                               _attrs_amplatz_dilator),
    "MFUASDXXDDLL":    (["MFUASD"],                               _attrs_amplatz_sheath_dil),
    "MFUADSXXDDLLH":   (["MFUADS"],                               _attrs_amplatz_set),
    "MFUASXXDDddLL":   (["MFUAS0"],                               _attrs_amplatz_sheath),
    "BCCCVDDLL":       (["BUUC","MFUUC"],                         _attrs_ureteral_catheter),
    "BIBCVDDLL":       ([],                                        _attrs_generic),
    "MFUSBVDDCCLLX":   (["MFUSB","BUSB"],                         _attrs_stone_basket),
    "MFUGPVDDCCLLX":   (["MFUGP","BUGP"],                         _attrs_gpaw),
    "MFUSGVDDCCLLX":   (["MFUSG","BUSG"],                         _attrs_stone_grasper),
    "MFUYYVDDAALLX":   ([],                                        _attrs_generic),
    "BCBGVDDLL":       ([],                                        _attrs_generic),
    "BCCNVDDLL":       ([],                                        _attrs_generic),
    "BCIPNVDDLL":      ([],                                        _attrs_generic),
    "MFUESVDDLL":      ([],                                        _attrs_generic),
    "MFUFDVDDLL":      ([],                                        _attrs_generic),
    "BCFDVDDLLH":      ([],                                        _attrs_generic),
    "MFUDLCVDDLLH":    (["MFUDLC"],                               _attrs_dual_lumen),
    "BCGWVDDLL":       ([],                                        _attrs_generic),
    "MFUUASVDDCCLLH":  (["MFUUAS","BUUAS"],                       _attrs_access_sheath),
}

# ---------------------------------------------------------------------------
# Long Life DJ — derive from MFDJA* codes (same builder as DJ)
# We'll inject this as a sibling entry under key "MFDJAV00DDLLHX"
# ---------------------------------------------------------------------------
LONG_LIFE_PREFIXES = ["MFDJA","MFDJC","MFDJD","MFDJI","MFDJH"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_logging()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Reading index docs from %s", INDEX_IN)
    with open(INDEX_IN, encoding="utf-8") as f:
        index_docs: dict = json.load(f)

    logger.info("Loading master rows from %s", MASTER_PATH)
    master_rows = _load_master()
    logger.info("Loaded %d unique product rows", len(master_rows))

    new_index: dict = {}

    for template, entry in tqdm(index_docs.items(), desc="Building template attributes", unit="template"):
        # Deep-copy the existing entry structure
        new_entry: dict = json.loads(json.dumps(entry))

        # Lookup builder
        if template in TEMPLATE_MAP:
            prefixes, builder = TEMPLATE_MAP[template]
        else:
            prefixes, builder = [], _attrs_generic

        # Collect bracket groups from matching master rows
        groups = _collect_brackets(master_rows, prefixes)
        logger.info(
            "[%s] %s | %d bracket groups from %d prefix(es)",
            template,
            entry.get("name", "?"),
            len(groups),
            len(prefixes),
        )

        # Build attribute block
        attrs = builder(groups) if groups or builder is not _attrs_generic else _attrs_generic()

        if attrs:
            new_entry["attributes"] = attrs

        new_index[template] = new_entry

    # ---------------------------------------------------------------------------
    # Add Long Life DJ Stent as a separate entry (not in index_docs but distinct)
    # ---------------------------------------------------------------------------
    ll_template = "MFDJAV00DDLLHX"
    ll_groups = _collect_brackets(master_rows, LONG_LIFE_PREFIXES)
    logger.info("[LONG LIFE DJ] | %d bracket groups", len(ll_groups))

    long_life_entry = {
        "name": "LONG LIFE DJ STENT (360D)",
        "segments": {
            "MF":  "Marflow AG",
            "U":   "Urology",
            "DJ":  "Double J Stent (Long Life)",
            "A":   "Variant Type",
            "00":  "Variant Code",
            "DD":  "Size in FR",
            "LL":  "Length in CM",
        },
        "notes": "Long Life 360D stent — Nitinol-enhanced for extended indwell time",
        "attributes": _attrs_dj(ll_groups),
    }
    new_index[ll_template] = long_life_entry

    # ---------------------------------------------------------------------------
    # Write output
    # ---------------------------------------------------------------------------
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(new_index, f, indent=2, ensure_ascii=False)

    logger.info("Done -> %s (%d templates)", OUTPUT_PATH, len(new_index))


if __name__ == "__main__":
    main()
