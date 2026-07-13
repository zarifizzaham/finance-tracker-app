import streamlit as st


def show_welcome_guide():
    st.markdown("### How it works")
    st.write(
        "Upload your bank statement CSV files above to get started. "
        "This app breaks down your spending by category for each month and remembers your choices for future uploads."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**1 — Export from your bank**")
        st.caption("Log into your banking app and download your statement as a CSV. Most banks offer this under Statements or Account History.")
    with c2:
        st.markdown("**2 — Upload**")
        st.caption("Use the file uploader above. You can upload multiple months at once — each file becomes its own tab.")
    with c3:
        st.markdown("**3 — Categorise**")
        st.caption("In each month tab, assign categories to your outflows (e.g. Food, Transport, Subscriptions). Use the sidebar to add your own categories.")
    with c4:
        st.markdown("**4 — Analyse**")
        st.caption("View a spending breakdown by category, totals for the month, and compare months side-by-side in the Compare tab.")

    st.divider()

    st.markdown("**Supported banks (auto-detected)**")
    st.caption("Revolut · Monzo · Barclays · HSBC · Starling · Lloyds — if your bank isn't listed, you'll be prompted to map the columns once and it will be remembered.")

    st.info(
        "**Tip:** The app learns from your choices. Once you label 'Netflix' as Subscriptions, "
        "the same merchant is auto-categorised across all months — past and future."
    )
