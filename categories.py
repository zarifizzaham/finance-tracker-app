import streamlit as st
from persistence import (
    save_categories,
    outflow_overrides, inflow_overrides,
    make_tx_key,
    save_outflow_overrides, save_inflow_overrides,
)


def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        lowered = [kw.lower().strip() for kw in keywords]
        for idx, row in df.iterrows():
            if row["Amount"] > 0:
                continue
            if row["Description"].lower().strip() in lowered:
                df.at[idx, "Category"] = category
    return df


def add_keyword_to_category(category: str, keyword: str, save: bool = True) -> bool:
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        if save:
            save_categories()
        return True
    return False


def delete_category(cat_name: str):
    del st.session_state.categories[cat_name]
    save_categories()
    for month in st.session_state.months.values():
        for df_key in ["outflow_df", "inflow_df"]:
            df = month[df_key]
            df.loc[df["Category"] == cat_name, "Category"] = "Uncategorized"

    # Remove stale override entries so the deleted category isn't re-applied on next upload
    stale_out = [k for k, v in outflow_overrides.items() if v == cat_name]
    for k in stale_out:
        del outflow_overrides[k]
    if stale_out:
        save_outflow_overrides()

    stale_inf = [k for k, v in inflow_overrides.items() if v == cat_name]
    for k in stale_inf:
        del inflow_overrides[k]
    if stale_inf:
        save_inflow_overrides()
