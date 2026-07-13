from datetime import date

import streamlit as st
from categories import delete_category
from persistence import save_categories


def render_sidebar():
    with st.sidebar:
        st.header("Categories")
        st.caption(
            "Categories let you group your transactions (e.g. Food, Rent, Subscriptions). "
            "Once you label a merchant, the app remembers it across all months."
        )

        st.divider()
        st.subheader("Add Category")
        if "sidebar_new_cat_v" not in st.session_state:
            st.session_state.sidebar_new_cat_v = 0
        new_category = st.text_input(
            "Category name", placeholder="e.g. Groceries",
            key=f"sidebar_new_cat_{st.session_state.sidebar_new_cat_v}",
        )
        if "_cat_added_msg" in st.session_state:
            st.success(f"**{st.session_state.pop('_cat_added_msg')}** added.")

        if st.button("Add Category", type="primary", key="sidebar_add_cat") and new_category:
            if new_category not in st.session_state.categories:
                st.session_state.categories[new_category] = []
                save_categories()
                st.session_state.sidebar_new_cat_v += 1  # new key clears the widget on rerun
                st.session_state["_cat_added_msg"] = new_category
                st.rerun()
            else:
                st.warning(f"**{new_category}** already exists.")

        st.divider()
        st.subheader("Manage Categories")
        st.caption("Click ✕ to delete a category — affected transactions revert to Uncategorized.")

        for cat in list(st.session_state.categories.keys()):
            col1, col2 = st.columns([4, 1])
            col1.write(cat)
            if cat != "Uncategorized":
                if col2.button("✕", key=f"del_cat_{cat}", help=f"Delete {cat}"):
                    delete_category(cat)
                    st.rerun()

        # ── Download Report ────────────────────────────────────────────────────
        st.divider()
        st.subheader("Download Report")

        with st.expander("Before you download — checklist"):
            st.markdown(
                "Complete **all four steps** before generating:\n\n"
                "1. **Upload CSV files** — at least one month must be loaded\n"
                "2. **Categorise every transaction** — open each month tab, fix any "
                "*Uncategorized* rows, and click **Apply Changes**\n"
                "3. **Enter your monthly take-home pay** in the 50/30/20 Rule tab\n"
                "4. **Assign Needs and Wants** in the 50/30/20 Rule tab "
                "(Savings bucket is optional)\n\n"
                "The PDF includes: full transaction log, per-month expense charts, "
                "month comparison, and a 40-year savings projection."
            )

        has_months   = bool(st.session_state.get("months"))
        needs_cats   = st.session_state.get("5030_needs",   [])
        wants_cats   = st.session_state.get("5030_wants",   [])
        savings_cats = st.session_state.get("5030_savings", [])
        salary       = st.session_state.get("5030_salary",  0)

        errors = []
        if not has_months:
            errors.append("No bank statements uploaded yet.")
        else:
            uncategorized = sum(
                (m["outflow_df"]["Category"] == "Uncategorized").sum() +
                (m["inflow_df"]["Category"]  == "Uncategorized").sum()
                for m in st.session_state.months.values()
            )
            if uncategorized > 0:
                errors.append(
                    f"{uncategorized} transaction(s) still *Uncategorized* — "
                    "assign a category in each month tab."
                )
        if not needs_cats:
            errors.append("No **Needs** categories assigned — open the 50/30/20 Rule tab.")
        if not wants_cats:
            errors.append("No **Wants** categories assigned — open the 50/30/20 Rule tab.")
        if not salary:
            errors.append("Monthly take-home pay is zero — enter it in the 50/30/20 Rule tab.")

        if errors:
            if "_report_pdf" in st.session_state:
                del st.session_state["_report_pdf"]
            for e in errors:
                st.warning(e)
        else:
            if st.button("Generate Report", key="gen_report_btn", type="primary"):
                with st.spinner("Building PDF — rendering charts..."):
                    from ui.report import generate_report_pdf
                    st.session_state["_report_pdf"] = generate_report_pdf(
                        salary, needs_cats, wants_cats, savings_cats
                    )

            if "_report_pdf" in st.session_state:
                st.download_button(
                    "Download Report PDF",
                    data=st.session_state["_report_pdf"],
                    file_name=f"finance_report_{date.today().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    key="dl_report_btn",
                )
                st.caption("Re-click **Generate Report** if you've made changes since last generation.")
