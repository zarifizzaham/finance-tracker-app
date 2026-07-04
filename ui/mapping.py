import streamlit as st
from config import DATE_FORMAT_OPTIONS


def show_mapping_ui(raw_df, suffix: str = "") -> dict | None:
    st.warning("Bank format not recognised. Map your columns below so the app knows how to read your CSV.")
    st.dataframe(raw_df.head(3), use_container_width=True, hide_index=True)

    cols = list(raw_df.columns)
    c1, c2, c3, c4 = st.columns(4)
    date_col  = c1.selectbox("Date column",        cols, key=f"map_date_{suffix}")
    desc_col  = c2.selectbox("Description column", cols, key=f"map_desc_{suffix}")
    fmt_label = c4.selectbox("Date format",        list(DATE_FORMAT_OPTIONS.keys()), key=f"map_fmt_{suffix}")

    split = st.checkbox("Amount is split into two columns (debit/credit)", key=f"map_split_{suffix}")

    if split:
        cs1, cs2 = st.columns(2)
        debit_col  = cs1.selectbox("Debit column (money out)", cols, key=f"map_debit_{suffix}")
        credit_col = cs2.selectbox("Credit column (money in)", cols, key=f"map_credit_{suffix}")
    else:
        amount_col = c3.selectbox("Amount column", cols, key=f"map_amount_{suffix}")

    if st.button("Save & Continue", type="primary", key=f"map_btn_{suffix}"):
        if split:
            return {
                "date_col":        date_col,
                "date_format":     DATE_FORMAT_OPTIONS[fmt_label],
                "description_col": desc_col,
                "debit_col":       debit_col,
                "credit_col":      credit_col,
            }
        return {
            "date_col":        date_col,
            "date_format":     DATE_FORMAT_OPTIONS[fmt_label],
            "description_col": desc_col,
            "amount_col":      amount_col,
        }
    return None
