import streamlit as st
from persistence import save_categories, outflow_overrides, make_tx_key


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


def add_keyword_to_category(category: str, keyword: str) -> bool:
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False


def propagate_category_to_all_months(description: str, category: str):
    """Update every loaded month's outflow_df and write an override key per matching row."""
    desc_lower = description.lower().strip()
    for month_data in st.session_state.months.values():
        df = month_data["outflow_df"]
        mask = df["Description"].str.lower().str.strip() == desc_lower
        df.loc[mask, "Category"] = category
        for _, row in df[mask].iterrows():
            outflow_overrides[make_tx_key(row)] = category


def delete_category(cat_name: str):
    del st.session_state.categories[cat_name]
    save_categories()
    for month in st.session_state.months.values():
        for df_key in ["outflow_df", "inflow_df"]:
            df = month[df_key]
            df.loc[df["Category"] == cat_name, "Category"] = "Uncategorized"
