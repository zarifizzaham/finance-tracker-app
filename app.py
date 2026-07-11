import base64
import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Simple Finance Tracking App", page_icon="🤑", layout="wide")

# All other imports come after set_page_config
from config import BANK_FORMATS
from ingestion import make_fingerprint, detect_bank, load_transactions, get_month_info
from persistence import (
    apply_inflow_overrides, apply_outflow_overrides,
    load_bank_mappings, save_bank_mappings,
)
from ui.mapping import show_mapping_ui
from ui.welcome import show_welcome_guide
from ui.sidebar import render_sidebar
from ui.month import render_month
from ui.comparison import render_comparison
from ui.budget_rule import render_5030_tab


@st.cache_data
def _load_bg_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _apply_css():
    img = _load_bg_image("image finance tracker.webp")
    st.markdown(f"""
<style>
.stApp {{
    background-image: url("data:image/webp;base64,{img}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stAppViewContainer"] {{
    background: rgba(0, 0, 0, 0.30);
}}
.block-container {{
    background: rgba(14, 17, 23, 0.55);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    padding: 2rem 3rem !important;
}}
[data-testid="stHeader"] {{
    background: rgba(0, 0, 0, 0.0);
}}
[data-testid="stSidebar"] {{
    background: rgba(14, 17, 23, 0.80);
    backdrop-filter: blur(10px);
}}
</style>
""", unsafe_allow_html=True)


def _init_session_state():
    """Initialize session state from disk on each new session (survives F5)."""
    if "categories" not in st.session_state:
        st.session_state.categories = {"Uncategorized": [], "New category": []}
        if os.path.exists("categories.json"):
            try:
                with open("categories.json", "r") as f:
                    st.session_state.categories = json.load(f)
            except (json.JSONDecodeError, OSError):
                st.warning("categories.json is corrupted — starting with default categories.")

    if "months" not in st.session_state:
        st.session_state.months = {}


def main():
    _apply_css()
    _init_session_state()

    st.title("Simple Finance Dashboard")
    st.divider()

    st.info(
        "**Before uploading:** each CSV file must contain transactions from a **single calendar month** only. "
        "If a file spans multiple months, the app will group all transactions under whichever month appears most "
        "frequently and the date ranges will be wrong. Export a separate file per month from your banking app before uploading."
    )

    uploaded_files = st.file_uploader(
        "Upload your bank statement CSV files — one file per month, multiple files supported",
        type=["csv"],
        accept_multiple_files=True,
    )

    render_sidebar()

    if not uploaded_files:
        st.session_state.months = {}
        show_welcome_guide()
        return

    current_names = {f.name for f in uploaded_files}

    # Remove months where any source file was deselected; remaining files re-merge below
    for mk in list(st.session_state.months.keys()):
        if not st.session_state.months[mk]["filenames"].issubset(current_names):
            del st.session_state.months[mk]

    bank_mappings   = load_bank_mappings()
    processed_names = {name for v in st.session_state.months.values() for name in v["filenames"]}

    # Process any newly added files
    for uploaded_file in uploaded_files:
        if uploaded_file.name in processed_names:
            continue

        try:
            raw_df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read **{uploaded_file.name}**: {e}")
            continue
        raw_df.columns = [col.strip() for col in raw_df.columns]
        uploaded_file.seek(0)

        fingerprint = make_fingerprint(raw_df.columns)
        bank_name   = detect_bank(raw_df.columns)
        fmt         = None

        if bank_name:
            fmt = BANK_FORMATS[bank_name]
        elif fingerprint in bank_mappings:
            fmt       = bank_mappings[fingerprint]
            bank_name = "Custom"

        if fmt is None:
            continue  # handled by mapping UI below

        df = load_transactions(uploaded_file, fmt)
        if df is not None:
            if df.empty:
                st.warning(f"**{uploaded_file.name}** has no valid transactions after parsing — skipping.")
                continue
            month_key, month_label = get_month_info(df)
            new_out = apply_outflow_overrides(df[df["Amount"] < 0].copy())
            new_inf = apply_inflow_overrides(df[df["Amount"] > 0].copy())
            def _sort_by_date(df):
                return df.sort_values(["Date", "Description"], ascending=True).reset_index(drop=True)

            if month_key in st.session_state.months:
                existing = st.session_state.months[month_key]
                existing["outflow_df"] = _sort_by_date(pd.concat([existing["outflow_df"], new_out], ignore_index=True))
                existing["inflow_df"]  = _sort_by_date(pd.concat([existing["inflow_df"],  new_inf],  ignore_index=True))
                existing["filenames"].add(uploaded_file.name)
                existing["banks"].append(bank_name)
            else:
                st.session_state.months[month_key] = {
                    "banks":       [bank_name],
                    "month_label": month_label,
                    "filenames":   {uploaded_file.name},
                    "outflow_df":  _sort_by_date(new_out),
                    "inflow_df":   _sort_by_date(new_inf),
                }

    # Show mapping UI for any file still unrecognised
    processed_names = {name for v in st.session_state.months.values() for name in v["filenames"]}
    for uploaded_file in uploaded_files:
        if uploaded_file.name in processed_names:
            continue
        uploaded_file.seek(0)
        raw_df = pd.read_csv(uploaded_file)
        raw_df.columns = [col.strip() for col in raw_df.columns]
        fingerprint = make_fingerprint(raw_df.columns)
        if detect_bank(raw_df.columns) is None and fingerprint not in bank_mappings:
            st.subheader(f"Map columns for `{uploaded_file.name}`")
            fmt = show_mapping_ui(raw_df, suffix=uploaded_file.name)
            if fmt is not None:
                bank_mappings[fingerprint] = fmt
                save_bank_mappings(bank_mappings)
                st.rerun()

    if not st.session_state.months:
        return

    sorted_months = sorted(st.session_state.months.items())

    for _, month in sorted_months:
        st.success(f"Detected: **{', '.join(month['banks'])}** — {month['month_label']} loaded")

    all_tabs = st.tabs(
        [m["month_label"] for _, m in sorted_months] + ["Compare Months", "50/30/20 Rule"]
    )

    for tab, (month_key, _) in zip(all_tabs[:-2], sorted_months):
        with tab:
            render_month(month_key)

    with all_tabs[-2]:
        render_comparison()

    with all_tabs[-1]:
        render_5030_tab()


main()
