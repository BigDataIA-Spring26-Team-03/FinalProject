"""Page 2 — Example ETL Transformations across all three data sources."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POC_ROOT = Path(__file__).parent.parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

import pandas as pd
import streamlit as st

from src.parse import _split_hts_and_stat_suffix, _hts_level, CHAPTER_TO_SECTION
from src.source2.parse import clean_html
from src.source2.fetch import fetch_full_text
from src.source2.extract_hts import extract_hts_codes
from utils.snowflake_conn import get_connection, run_query

st.set_page_config(page_title="Transformations — TariffIQ POC", page_icon="🔄", layout="wide")
st.title("🔄 Example Transformations")
st.caption("Step-by-step walkthrough of the key ETL transformations in each pipeline stage.")

# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORM 1 — HTS Code Splitting
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🔢 Transform 1 — HTS Code Splitting (Source 1)", expanded=True):
    st.markdown(
        """
        The USITC API returns `htsno` in several inconsistent formats.
        The parser normalises every format into a clean **8-digit HTS_CODE** and a 2-digit **STAT_SUFFIX**.

        > *Why it matters:* downstream SQL lookups use `HTS_CODE LIKE '8471%'` — the split must be exact.
        """
    )

    SAMPLES = [
        "8471.30.01.00",
        "8471.300100",
        "0101.21.00.10",
        "6110.20.2079",
        "9903.88.01",
        "7208.10.15.00",
        "84",
        "8471",
        "0201.10.0010",
        "3926.90.9990",
    ]

    records = []
    for s in SAMPLES:
        hts_code, stat_suffix = _split_hts_and_stat_suffix(s)
        level = _hts_level(hts_code)
        records.append({
            "Raw `htsno`": s,
            "HTS_CODE": hts_code or "(none)",
            "STAT_SUFFIX": stat_suffix or "(none)",
            "LEVEL": level,
        })

    df = pd.DataFrame(records)

    LEVEL_COLORS = {
        "statistical": "background-color: #d5f5e3; color: #1a1a1a",
        "subheading": "background-color: #d6eaf8; color: #1a1a1a",
        "heading": "background-color: #fef9e7; color: #1a1a1a",
        "chapter": "background-color: #fdebd0; color: #1a1a1a",
        "header": "background-color: #f2f3f4; color: #1a1a1a",
    }

    def color_level(val):
        return LEVEL_COLORS.get(val, "")

    st.dataframe(
        df.style.applymap(color_level, subset=["LEVEL"]),
        use_container_width=True,
        height=350,
    )
    st.caption(
        "Color legend — 🟢 Statistical (leaf level) · 🔵 Subheading · 🟡 Heading · 🟠 Chapter · ⬜ Header (structural row)"
    )

# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORM 2 — Level Classification + Chapter-to-Section Mapping
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🗂️ Transform 2 — Level Classification & Chapter-to-Section Mapping (Source 1)"):
    st.markdown(
        """
        Each HTS code is classified into one of five hierarchy levels based on its dot-count structure,
        and mapped to one of 21 HTS sections for coarse-grained grouping.
        """
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Level Classification Rules")
        rules = pd.DataFrame([
            {"Dot Count": "0, len ≤ 2", "Level": "chapter", "Example": "84"},
            {"Dot Count": "0, len > 2", "Level": "heading", "Example": "8471"},
            {"Dot Count": "1", "Level": "subheading", "Example": "8471.30"},
            {"Dot Count": "≥ 2", "Level": "statistical", "Example": "8471.30.01"},
            {"Dot Count": "(empty)", "Level": "header", "Example": "(blank row)"},
        ])
        st.dataframe(rules, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("Chapter → Section Mapping (21 Sections)")
        SECTION_NAMES = {
            1: "Live Animals & Animal Products (Ch 1–5)",
            2: "Vegetable Products (Ch 6–14)",
            3: "Fats & Oils (Ch 15)",
            4: "Prepared Foodstuffs & Tobacco (Ch 16–24)",
            5: "Mineral Products (Ch 25–27)",
            6: "Chemical Industry Products (Ch 28–38)",
            7: "Plastics & Rubber (Ch 39–40)",
            8: "Raw Hides & Leather (Ch 41–43)",
            9: "Wood & Wood Articles (Ch 44–46)",
            10: "Pulp of Wood & Paper (Ch 47–49)",
            11: "Textiles & Textile Articles (Ch 50–63)",
            12: "Footwear & Headgear (Ch 64–67)",
            13: "Stone, Cement & Glass (Ch 68–70)",
            14: "Precious Metals & Stones (Ch 71)",
            15: "Base Metals & Articles (Ch 72–83)",
            16: "Machinery & Mechanical Appliances (Ch 84–85)",
            17: "Vehicles, Aircraft & Vessels (Ch 86–89)",
            18: "Optical & Medical Instruments (Ch 90–92)",
            19: "Arms & Ammunition (Ch 93)",
            20: "Miscellaneous Manufactured Articles (Ch 94–96)",
            21: "Works of Art & Special Classification (Ch 97–99)",
        }
        section_df = pd.DataFrame([
            {"Section": sec, "Section Name": name}
            for sec, name in SECTION_NAMES.items()
        ])
        st.dataframe(section_df, use_container_width=True, height=350, hide_index=True)

    st.caption(
        "The `_section_number(chapter)` function uses the `CHAPTER_TO_SECTION` dict "
        "(`src/parse.py`) built from the official HTS section-chapter mapping."
    )
