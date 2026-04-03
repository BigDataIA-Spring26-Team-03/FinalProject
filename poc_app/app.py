"""TariffIQ POC — Streamlit entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="TariffIQ POC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 TariffIQ — Proof of Concept")
st.caption("Conversational multi-agent RAG system for US import tariff intelligence")

st.markdown("---")

col1, col2 = st.columns([1.6, 1])

with col1:
    st.subheader("What is TariffIQ?")
    st.markdown(
        """
        US import tariff data is scattered across **three disconnected government systems**:

        | Source | System | Contains |
        |---|---|---|
        | **Source 1** | USITC Harmonized Tariff Schedule | 35,733 product codes + duty rates |
        | **Source 2** | Federal Register (USTR Notices) | Legal text behind every tariff action |
        | **Source 3** | Census Bureau Trade API | Monthly import volumes by country |

        A procurement manager asking *"What is the tariff on laptops from China, and has it changed recently?"*
        must currently visit all three systems manually, find the relevant documents, and synthesize the answer
        themselves. **TariffIQ automates this.**
        """
    )

with col2:
    st.subheader("Multi-Agent Pipeline")
    st.markdown(
        """
        ```
        User Query (plain English)
               ↓
        [1] Query Agent  ← Claude Haiku
               ↓ structured intent
        [2] Classification Agent  ← Snowflake
               ↓ HTS code + confidence
        [3] Rate Agent  ← Snowflake (SQL only)
               ↓ duty rates + record IDs
        [4] Policy Agent  ← Federal Register RAG
               ↓ cited policy context
        [5] Trade Agent  ← Census Bureau API
               ↓ import volume trends
        [6] Synthesis Agent  ← Claude Sonnet
               ↓
        Cited answer (grounded, no hallucination)
        ```
        """
    )

st.markdown("---")

st.subheader("Navigate this POC")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("**📈 1 — EDA**\n\nExploratory analysis of all three data sources with live charts and metrics.")
with c2:
    st.info("**🔄 2 — Transformations**\n\nStep-by-step ETL pipeline walkthrough with before/after comparisons.")
with c3:
    st.info("**🤖 3 — LLM Experiments**\n\nFirst Claude integrations: query parsing and rate interpretation.")

st.markdown("---")
st.caption(
    "Data sources: USITC HTS API · Federal Register API · US Census Bureau International Trade API  |  "
    "LLM: Claude (Anthropic) via Anthropic SDK  |  Storage: Snowflake"
)
