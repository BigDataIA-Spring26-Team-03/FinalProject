"""Page 1 — Preliminary Exploratory Data Analysis across all three sources."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure utils/ (poc_app/utils/) is importable
POC_ROOT = Path(__file__).parent.parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.snowflake_conn import get_connection, run_query
from src.source3.fetch import get_trend, COUNTRY_CODES

st.set_page_config(page_title="EDA — TariffIQ POC", page_icon="📈", layout="wide")
st.title("📈 Preliminary EDA")
st.caption("Exploratory analysis of all three data sources: USITC HTS · Federal Register · Census Bureau")

# ── Snowflake connection check ────────────────────────────────────────────────
try:
    conn = get_connection()
    st.success("Connected to Snowflake", icon="✅")
except Exception as e:
    st.error(f"Snowflake connection failed: {e}")
    st.stop()

tab1, tab2, tab3 = st.tabs(
    ["📦 Source 1: HTS Codes", "📄 Source 2: Policy Notices", "🌐 Source 3: Trade Data"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HTS_CODES
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Source 1 — USITC Harmonized Tariff Schedule")
    st.markdown(
        "35,733 product codes fetched from the USITC REST API, parsed, and loaded into Snowflake. "
        "Header rows (structural rows without an HTS code) are excluded from analysis."
    )

    @st.cache_data(ttl=3600)
    def load_hts_overview():
        total = run_query("SELECT COUNT(*) AS n FROM HTS_CODES")[0]["N"]
        actual = run_query(
            "SELECT COUNT(*) AS n FROM HTS_CODES WHERE IS_HEADER_ROW = FALSE AND HTS_CODE IS NOT NULL"
        )[0]["N"]
        chapters = run_query(
            "SELECT COUNT(DISTINCT CHAPTER) AS n FROM HTS_CODES WHERE CHAPTER IS NOT NULL"
        )[0]["N"]
        sections = run_query(
            "SELECT COUNT(DISTINCT SECTION_NUMBER) AS n FROM HTS_CODES WHERE SECTION_NUMBER IS NOT NULL"
        )[0]["N"]
        return total, actual, chapters, sections

    total, actual, chapters, sections = load_hts_overview()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", f"{total:,}")
    m2.metric("Actual Tariff Lines", f"{actual:,}")
    m3.metric("HTS Chapters", f"{chapters:,}")
    m4.metric("HTS Sections", f"{sections:,}")

    st.markdown("---")
    col_a, col_d = st.columns(2)

    with col_a:
        @st.cache_data(ttl=3600)
        def load_level_dist():
            return run_query(
                "SELECT LEVEL, COUNT(*) AS CNT FROM HTS_CODES "
                "WHERE IS_HEADER_ROW = FALSE GROUP BY LEVEL ORDER BY CNT DESC"
            )

        rows = load_level_dist()
        df_level = pd.DataFrame(rows)
        fig = px.bar(
            df_level, x="LEVEL", y="CNT", color="LEVEL",
            title="HTS Record Distribution by Level",
            labels={"LEVEL": "Hierarchy Level", "CNT": "Record Count"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, key="hts_level_dist")
        st.caption(
            "**Statistical** rows are the leaf-level product lines used for actual import classification. "
            "**Subheading** and **heading** rows structure the hierarchy."
        )

    with col_d:
        SECTION_NAMES = {
            1: "Live Animals & Animal Products",
            2: "Vegetable Products",
            3: "Animal or Vegetable Fats & Oils",
            4: "Prepared Foodstuffs & Tobacco",
            5: "Mineral Products",
            6: "Chemical Industry Products",
            7: "Plastics & Rubber",
            8: "Raw Hides, Skins & Leather",
            9: "Wood & Wood Articles",
            10: "Pulp of Wood & Paper",
            11: "Textiles & Textile Articles",
            12: "Footwear, Headgear",
            13: "Stone, Cement & Glass Articles",
            14: "Precious Metals & Stones",
            15: "Base Metals & Articles",
            16: "Machinery & Mechanical Appliances",
            17: "Vehicles, Aircraft & Vessels",
            18: "Optical & Medical Instruments",
            19: "Arms & Ammunition",
            20: "Miscellaneous Manufactured Articles",
            21: "Works of Art & Special Classification",
        }

        @st.cache_data(ttl=3600)
        def load_section_dist():
            return run_query(
                "SELECT SECTION_NUMBER, COUNT(*) AS CNT FROM HTS_CODES "
                "WHERE IS_HEADER_ROW = FALSE AND SECTION_NUMBER IS NOT NULL "
                "AND LEVEL = 'statistical' "
                "GROUP BY SECTION_NUMBER ORDER BY SECTION_NUMBER"
            )

        rows = load_section_dist()
        df_sec = pd.DataFrame(rows)
        df_sec["SECTION_NAME"] = df_sec["SECTION_NUMBER"].map(SECTION_NAMES)
        df_sec["LABEL"] = "Sec " + df_sec["SECTION_NUMBER"].astype(str)
        fig = px.treemap(
            df_sec, path=["LABEL"], values="CNT",
            title="Statistical Lines by HTS Section (Treemap)",
            color="CNT", color_continuous_scale="Teal",
            hover_data={"SECTION_NAME": True},
        )
        fig.update_traces(textinfo="label+value")
        st.plotly_chart(fig, use_container_width=True, key="hts_section_treemap")
        st.caption("Section 16 (Machinery) and Section 11 (Textiles) have the most granular product classification.")

    st.markdown("---")
    st.subheader("Sample HTS Records")

    @st.cache_data(ttl=3600)
    def load_sample_hts():
        return run_query(
            "SELECT HTS_CODE, DESCRIPTION, LEVEL, GENERAL_RATE, SPECIAL_RATE, CHAPTER "
            "FROM HTS_CODES WHERE IS_HEADER_ROW = FALSE AND HTS_CODE IS NOT NULL "
            "AND LEVEL IN ('subheading', 'statistical') AND GENERAL_RATE != '' "
            "LIMIT 20"
        )

    sample = load_sample_hts()
    st.dataframe(pd.DataFrame(sample), use_container_width=True, height=300)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FEDERAL_REGISTER_NOTICES
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Source 2 — Federal Register (USTR Tariff Notices)")
    st.markdown(
        "Tariff notices published by the Office of the United States Trade Representative (USTR) "
        "since 2018, ingested via the Federal Register REST API. HTS codes extracted from full-text "
        "bodies using regex and cross-referenced to Source 1."
    )

    @st.cache_data(ttl=3600)
    def load_fr_overview():
        total = run_query("SELECT COUNT(*) AS N FROM FEDERAL_REGISTER_NOTICES")[0]["N"]
        min_max = run_query(
            "SELECT MIN(PUBLICATION_DATE) AS MIN_D, MAX(PUBLICATION_DATE) AS MAX_D "
            "FROM FEDERAL_REGISTER_NOTICES WHERE PUBLICATION_DATE IS NOT NULL"
        )[0]
        chaps = run_query(
            "SELECT COUNT(DISTINCT HTS_CHAPTER) AS N FROM NOTICE_HTS_CODES WHERE HTS_CHAPTER IS NOT NULL"
        )[0]["N"]
        mentions = run_query("SELECT COUNT(*) AS N FROM NOTICE_HTS_CODES")[0]["N"]
        return total, min_max, chaps, mentions

    total, min_max, chaps, mentions = load_fr_overview()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Notices Ingested", f"{total:,}")
    m2.metric("Date Range", f"{min_max.get('MIN_D', 'N/A')} → {min_max.get('MAX_D', 'N/A')}")
    m3.metric("HTS Chapters Targeted", f"{chaps:,}")
    m4.metric("HTS Code Mentions Extracted", f"{mentions:,}")

    st.markdown("---")

    @st.cache_data(ttl=3600)
    def load_top_chapters_fr():
        return run_query(
            "SELECT HTS_CHAPTER, COUNT(DISTINCT DOCUMENT_NUMBER) AS DOC_COUNT "
            "FROM NOTICE_HTS_CODES WHERE HTS_CHAPTER IS NOT NULL "
            "GROUP BY HTS_CHAPTER ORDER BY DOC_COUNT DESC LIMIT 15"
        )

    rows = load_top_chapters_fr()
    df_chfr = pd.DataFrame(rows)
    df_chfr["HTS_CHAPTER"] = df_chfr["HTS_CHAPTER"].astype(str)
    fig = px.bar(
        df_chfr, x="HTS_CHAPTER", y="DOC_COUNT",
        title="Top 15 HTS Chapters Targeted by Tariff Notices",
        labels={"HTS_CHAPTER": "HTS Chapter", "DOC_COUNT": "Distinct Notices"},
        color="DOC_COUNT", color_continuous_scale="Reds",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True, key="fr_top_chapters")
    st.caption("Chapter 84–85 (electronics/machinery) and Chapter 72–73 (steel) appear most frequently in USTR notices.")

    st.markdown("---")
    st.subheader("Cross-Source Join: HTS Codes in Policy Documents")
    st.caption("Top HTS codes mentioned in Federal Register notices, joined to their duty rates from Source 1.")

    @st.cache_data(ttl=3600)
    def load_cross_join():
        return run_query(
            """
            SELECT
                h.HTS_CODE,
                c.DESCRIPTION,
                c.GENERAL_RATE,
                COUNT(DISTINCT h.DOCUMENT_NUMBER) AS MENTION_COUNT
            FROM NOTICE_HTS_CODES h
            JOIN HTS_CODES c ON h.HTS_CODE = c.HTS_CODE
            WHERE c.IS_HEADER_ROW = FALSE AND c.GENERAL_RATE != ''
            GROUP BY h.HTS_CODE, c.DESCRIPTION, c.GENERAL_RATE
            ORDER BY MENTION_COUNT DESC
            LIMIT 20
            """
        )

    cross = load_cross_join()
    df_cross = pd.DataFrame(cross)
    st.dataframe(df_cross, use_container_width=True, height=300)

    st.markdown("---")
    st.subheader("View a Real Notice")

    @st.cache_data(ttl=3600)
    def load_sample_notice():
        rows = run_query(
            """
            SELECT n.DOCUMENT_NUMBER, n.TITLE, n.PUBLICATION_DATE, n.ABSTRACT, h.HTS_CODE, h.CONTEXT_SNIPPET
            FROM FEDERAL_REGISTER_NOTICES n
            JOIN NOTICE_HTS_CODES h ON n.DOCUMENT_NUMBER = h.DOCUMENT_NUMBER
            WHERE n.ABSTRACT IS NOT NULL AND h.CONTEXT_SNIPPET IS NOT NULL
            LIMIT 1
            """
        )
        return rows[0] if rows else None

    notice = load_sample_notice()
    if notice:
        with st.expander(f"📄 {notice.get('TITLE', 'N/A')}"):
            st.write(f"**Document Number:** {notice.get('DOCUMENT_NUMBER')}")
            st.write(f"**Published:** {notice.get('PUBLICATION_DATE')}")
            st.write(f"**Abstract:** {notice.get('ABSTRACT', '')}")
            st.markdown("---")
            st.write(f"**Extracted HTS Code:** `{notice.get('HTS_CODE')}`")
            st.write(f"**Context in Document:** *{notice.get('CONTEXT_SNIPPET', '')}*")
    else:
        st.info("No notices with both abstract and HTS codes found.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CENSUS TRADE DATA
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Source 3 — US Census Bureau International Trade API")
    st.markdown(
        "Live Census Bureau data queried at request time (no bulk cache). "
        "Shows monthly import values by HS product code and trading partner country."
    )
    st.info(
        "⏱ **Note:** Census data has a 2–3 month reporting lag. Results are cached for 1 hour. "
        "The API only supports HS6 granularity (4-digit prefix used here).",
        icon="ℹ️",
    )

    PRODUCTS = {
        "8471 — Computers & Laptops": "8471",
        "8541 — Solar Panels (Diodes/Transistors)": "8541",
        "7208 — Steel (Flat-Rolled)": "7208",
        "8517 — Smartphones & Telephones": "8517",
    }
    COUNTRIES_DISPLAY = {
        "China": "5700",
        "Mexico": "2010",
        "Canada": "1220",
        "Japan": "5490",
        "Vietnam": "5350",
        "Germany": "4120",
    }

    col_sel1, col_sel2 = st.columns(2)
    selected_product_label = col_sel1.selectbox("Select Product", list(PRODUCTS.keys()))
    selected_country = col_sel2.selectbox("Select Country", list(COUNTRIES_DISPLAY.keys()))

    hs_prefix = PRODUCTS[selected_product_label]
    country_code = COUNTRIES_DISPLAY[selected_country]

    @st.cache_data(ttl=3600)
    def fetch_trend_cached(hs, cc):
        return get_trend(hs, cc, months_back=12, comm_lvl="HS4")

    with st.spinner(f"Fetching 12-month trend for {selected_product_label.split('—')[0].strip()} from {selected_country}..."):
        trend_data = fetch_trend_cached(hs_prefix, country_code)

    if not trend_data:
        st.warning("No Census data available for this product + country combination. Try a different selection.")
    else:
        df_trend = pd.DataFrame(trend_data)
        df_trend = df_trend[df_trend["import_value_usd"].notna()]

        if df_trend.empty:
            st.warning("All months returned null import values. Census may have suppressed this data.")
        else:
            fig = px.line(
                df_trend, x="period", y="import_value_usd", markers=True,
                title=f"Monthly Import Value: {selected_product_label.split('—')[0].strip()} from {selected_country}",
                labels={"period": "Month", "import_value_usd": "Import Value (USD)"},
                color_discrete_sequence=["#2ecc71"],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True, key="census_trend_line")

            peak_row = df_trend.loc[df_trend["import_value_usd"].idxmax()]
            trough_row = df_trend.loc[df_trend["import_value_usd"].idxmin()]
            latest = df_trend.iloc[-1]
            pct_change = (
                ((peak_row["import_value_usd"] - trough_row["import_value_usd"])
                 / trough_row["import_value_usd"] * 100)
                if trough_row["import_value_usd"] > 0 else 0
            )

            ma, mb, mc, md = st.columns(4)
            ma.metric("Peak Month", peak_row["period"], f"${peak_row['import_value_usd']:,.0f}")
            mb.metric("Trough Month", trough_row["period"], f"${trough_row['import_value_usd']:,.0f}")
            mc.metric("Peak vs Trough", f"{pct_change:+.1f}%")
            md.metric("Latest Month", latest["period"], f"${latest['import_value_usd']:,.0f}")

    st.markdown("---")
    st.subheader("Country Comparison Heatmap")
    st.caption(f"Import values for {selected_product_label.split('—')[0].strip()} across all 6 countries × 12 months.")

    HEATMAP_COUNTRIES = list(COUNTRIES_DISPLAY.items())  # [(name, code), ...]

    @st.cache_data(ttl=3600)
    def fetch_all_countries_trend(hs):
        results = {}
        for name, code in HEATMAP_COUNTRIES:
            data = get_trend(hs, code, months_back=12, comm_lvl="HS4")
            results[name] = {r["period"]: r["import_value_usd"] for r in data if r["import_value_usd"] is not None}
        return results

    with st.spinner("Fetching data for all countries (cached after first load)..."):
        all_country_data = fetch_all_countries_trend(hs_prefix)

    all_periods = sorted({p for v in all_country_data.values() for p in v.keys()})
    if all_periods:
        heatmap_rows = []
        for country_name, period_data in all_country_data.items():
            row = {"Country": country_name}
            for period in all_periods:
                row[period] = period_data.get(period, 0) or 0
            heatmap_rows.append(row)

        df_heat = pd.DataFrame(heatmap_rows).set_index("Country")
        fig = px.imshow(
            df_heat,
            title=f"Import Value Heatmap — {selected_product_label.split('—')[0].strip()} (USD)",
            labels={"x": "Month", "y": "Country", "color": "Import Value (USD)"},
            color_continuous_scale="Blues",
            aspect="auto",
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True, key="census_heatmap")
        st.caption("Darker = higher import value. White cells = data suppressed or not available from Census.")
    else:
        st.warning("Insufficient data to build heatmap.")
