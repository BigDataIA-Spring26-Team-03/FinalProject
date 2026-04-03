"""Page 3 — LLM Experiment: Tariff Rate Interpretation via Claude."""

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

from utils.snowflake_conn import run_query

st.set_page_config(page_title="LLM Experiments — TariffIQ POC", page_icon="🤖", layout="wide")
st.title("🤖 LLM Experiments")
st.caption("Claude integration demo: tariff rate interpretation.")

# ── API connection check ──────────────────────────────────────────────────────
try:
    import anthropic
    client = anthropic.Anthropic()
    test = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        messages=[{"role": "user", "content": "ping"}],
    )
    st.success("Claude API connected (claude-haiku-4-5-20251001 ready)", icon="✅")
except ImportError:
    st.error("anthropic package not installed. Run: pip install anthropic")
    st.stop()
except Exception as e:
    st.error(f"Claude API connection failed: {e}. Check ANTHROPIC_API_KEY in your .env file.")
    st.stop()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT — Tariff Rate Interpretation
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📖 Tariff Rate Interpretation (Claude Haiku)")
st.info(
    "Raw HTS general rate strings are opaque to non-experts: `0.3¢/kg + 6.3%`, "
    "`The rate applicable in column 2`, `25% + $1.01/kg`. "
    "Claude interprets these in plain English, adding value that SQL alone cannot provide.",
    icon="ℹ️",
)


@st.cache_data(ttl=3600)
def load_complex_rates():
    return run_query(
        """
        SELECT DISTINCT GENERAL_RATE, DESCRIPTION
        FROM HTS_CODES
        WHERE IS_HEADER_ROW = FALSE
          AND GENERAL_RATE IS NOT NULL
          AND (GENERAL_RATE LIKE '%¢%' OR GENERAL_RATE LIKE '%+%')
          AND LENGTH(GENERAL_RATE) > 3
          AND DESCRIPTION IS NOT NULL
          AND LENGTH(DESCRIPTION) > 10
          AND LEVEL IN ('subheading', 'statistical')
        LIMIT 10
        """
    )


@st.cache_data(ttl=7200)
def interpret_all_rates(_client_placeholder, rates_and_descs):
    results = []
    for rate, desc in rates_and_descs:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=120,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Explain this US import tariff rate in one plain English sentence. "
                            f"Be specific about what the rate means for an importer.\n\n"
                            f"Rate: {rate}\n"
                            f"Product: {desc[:100]}"
                        ),
                    }
                ],
            )
            interpretation = response.content[0].text.strip()
        except Exception as e:
            interpretation = f"(Error: {e})"
        results.append({
            "Rate String": rate,
            "Product (truncated)": desc[:70],
            "Claude's Interpretation": interpretation,
        })
    return results


complex_rates = load_complex_rates()

if not complex_rates:
    st.warning("No complex rate strings found in Snowflake. Run main.py to load HTS data first.")
else:
    rate_tuples = tuple((r["GENERAL_RATE"], r["DESCRIPTION"]) for r in complex_rates)

    with st.spinner("Claude is interpreting 10 complex tariff rate strings (cached after first load)…"):
        interpreted = interpret_all_rates(None, rate_tuples)

    df_interp = pd.DataFrame(interpreted)
    st.dataframe(df_interp, use_container_width=True, height=380)
    st.caption(
        "In the full TariffIQ pipeline, interpreted rate descriptions are included in the Synthesis Agent's "
        "context so the final answer explains duty costs in plain English, not raw HTS notation."
    )
