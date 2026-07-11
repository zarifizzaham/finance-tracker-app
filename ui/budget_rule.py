import streamlit as st
import pandas as pd
import plotly.express as px


def render_5030_tab():

    def future_value(pmt, annual_rate, n_months):
        if pmt == 0:
            return 0.0
        if annual_rate == 0:
            return float(pmt * n_months)
        r = annual_rate / 12
        return pmt * ((1 + r) ** n_months - 1) / r

    SCENARIOS = {
        "Cash savings (0%)":            0.00,
        "Easy access savings (3%)":     0.03,
        "Index fund / Stocks ISA (7%)": 0.07,
    }
    MILESTONES = {1: 12, 5: 60, 10: 120, 20: 240, 40: 480}
    MAX_MONTHS = 500

    def projection_chart(monthly_pmt, title):
        rows = [
            {"Month": m, "Scenario": label, "Value (£)": future_value(monthly_pmt, rate, m)}
            for m in range(1, MAX_MONTHS + 1)
            for label, rate in SCENARIOS.items()
        ]
        fig = px.line(pd.DataFrame(rows), x="Month", y="Value (£)", color="Scenario", title=title)
        for years, month_n in MILESTONES.items():
            fig.add_vline(
                x=month_n, line_dash="dot", line_color="rgba(160,160,160,0.5)",
                annotation_text=f"{years}yr", annotation_position="top left",
                annotation_font_size=10,
            )
        fig.add_hline(
            y=monthly_pmt * MAX_MONTHS, line_dash="dot", line_color="rgba(160,160,160,0.4)",
            annotation_text="Total contributed", annotation_position="bottom right",
        )
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        return fig

    def milestone_table(monthly_pmt):
        rows = []
        for label, rate in SCENARIOS.items():
            row = {"Scenario": label}
            for years, month_n in MILESTONES.items():
                row[f"{years} yr"] = f"£{future_value(monthly_pmt, rate, month_n):,.0f}"
            rows.append(row)
        return pd.DataFrame(rows).set_index("Scenario")

    # ── A: The Rule ────────────────────────────────────────────────────────────
    st.header("50 / 30 / 20 Budget Rule")
    st.write(
        "A simple framework that divides your **monthly take-home pay** (after tax) into three buckets — "
        "needs, wants, and savings — giving every pound a purpose without a line-by-line budget."
    )

    with st.expander("What does each allocation cover?"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Needs — 50%**")
            st.caption("Non-negotiable essentials you cannot cut without serious consequences.")
            st.markdown("- Rent or mortgage\n- Groceries\n- Utilities\n- Transport\n- Minimum debt repayments")
        with c2:
            st.markdown("**Wants — 30%**")
            st.caption("Lifestyle choices — enjoyable, but reducible if needed.")
            st.markdown("- Dining out & takeaways\n- Streaming subscriptions\n- Gym\n- Holidays\n- Hobbies")
        with c3:
            st.markdown("**Savings & Debt — 20%**")
            st.caption("Pay yourself first — treat this as a fixed bill, not whatever is left over.")
            st.markdown("- Emergency fund (3–6 months)\n- Pension / ISA\n- Extra debt repayments\n- House deposit")

    st.divider()

    # ── B: Budget Calculator ───────────────────────────────────────────────────
    st.subheader("Budget Calculator")

    salary = st.number_input(
        "Monthly take-home pay (£)", min_value=0, value=1000, step=50,
        help="Enter your monthly salary or allowance after tax and deductions.",
        key="5030_salary",
    )

    target_20pct = int(salary * 0.20)
    slider_max   = max(target_20pct * 2, 200)

    monthly_savings = st.slider(
        "Monthly savings (£)",
        min_value=0, max_value=slider_max, value=target_20pct, step=10,
        help="The midpoint is the 20% target. Drag to explore different saving rates.",
        key="5030_slider",
    )

    savings_pct = (monthly_savings / salary * 100) if salary > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Needs — 50%", f"£{salary * 0.50:,.0f}", "target")
    c2.metric("Wants — 30%", f"£{salary * 0.30:,.0f}", "target")
    c3.metric(
        "Savings",
        f"£{monthly_savings:,.0f}",
        f"{savings_pct:.1f}% of take-home {'✓' if savings_pct >= 20 else '(target 20%)'}",
    )

    st.divider()

    # ── C: Hypothetical Projection ─────────────────────────────────────────────
    st.subheader("Savings Projection")
    st.caption(
        f"What £{monthly_savings:,}/month saved consistently grows into over "
        f"{MAX_MONTHS} months (~{MAX_MONTHS // 12} years). "
        "Dotted vertical lines mark 1, 5, 10, 20, and 40 year milestones."
    )

    st.plotly_chart(
        projection_chart(monthly_savings, f"Growth of £{monthly_savings:,}/month"),
        use_container_width=True,
    )
    st.dataframe(milestone_table(monthly_savings), use_container_width=True)

    st.caption(
        "Figures are illustrative. A 7% annual return approximates a long-run globally diversified index fund; "
        "actual returns vary. Past performance does not guarantee future results."
    )

    st.divider()

    # ── D: Your Actual Spending ────────────────────────────────────────────────
    st.subheader("Your Spending vs 50/30/20")

    if not st.session_state.months:
        st.info("Upload your bank statement CSV files to see how your real spending compares to the 50/30/20 rule.")
        return

    st.caption(
        "Assign your categories to Needs, Wants, and Savings below. "
        "Any unspent salary beyond those three buckets is also counted as savings."
    )

    available_cats = [c for c in st.session_state.categories if c != "Uncategorized"]

    prev_wants   = st.session_state.get("5030_wants", [])
    prev_savings = st.session_state.get("5030_savings", [])

    needs_options = [c for c in available_cats if c not in prev_wants and c not in prev_savings]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Needs** — essentials")
        needs_cats = st.multiselect(
            "needs_select", needs_options, key="5030_needs",
            label_visibility="collapsed",
        )
    with col2:
        wants_options = [c for c in available_cats if c not in needs_cats and c not in prev_savings]
        st.markdown("**Wants** — lifestyle")
        wants_cats = st.multiselect(
            "wants_select", wants_options, key="5030_wants",
            label_visibility="collapsed",
        )
    with col3:
        savings_options = [c for c in available_cats if c not in needs_cats and c not in wants_cats]
        st.markdown("**Savings** — pension, ISA, etc.")
        savings_cats = st.multiselect(
            "savings_select", savings_options, key="5030_savings",
            label_visibility="collapsed",
        )

    unassigned = [c for c in available_cats if c not in needs_cats and c not in wants_cats and c not in savings_cats]
    if unassigned:
        st.info(f"Not yet assigned: **{', '.join(unassigned)}**")

    if not (needs_cats or wants_cats or savings_cats):
        st.info("Assign at least one category to a bucket above to see your breakdown.")
        return

    if salary == 0:
        st.info("Enter your monthly take-home pay in the Budget Calculator above to see your breakdown.")
        return

    ideal_needs   = salary * 0.50
    ideal_wants   = salary * 0.30
    ideal_savings = salary * 0.20

    def delta_str(actual, ideal):
        diff = actual - ideal
        sign = "+" if diff >= 0 else ""
        return f"{sign}£{diff:,.0f} vs £{ideal:,.0f} target"

    def bucket_bar_fig(n, w, s, title, show_legend=True):
        df = pd.DataFrame({
            "Bucket":     ["Needs", "Wants", "Savings"] * 2,
            "Type":       ["Actual"] * 3 + ["50/30/20 Target"] * 3,
            "Amount (£)": [n, w, s, ideal_needs, ideal_wants, ideal_savings],
        })
        fig = px.bar(
            df, x="Bucket", y="Amount (£)", color="Type", barmode="group", title=title,
            color_discrete_map={"Actual": "#636efa", "50/30/20 Target": "#00cc96"},
        )
        fig.update_layout(showlegend=show_legend, margin=dict(t=40, b=20, l=10, r=10))
        return fig

    # Per-month charts
    st.markdown("**Breakdown by month**")
    sorted_month_keys = sorted(st.session_state.months.keys())
    COLS_PER_ROW = 3
    for i in range(0, len(sorted_month_keys), COLS_PER_ROW):
        batch = sorted_month_keys[i:i + COLS_PER_ROW]
        cols  = st.columns(len(batch))
        for col, mk in zip(cols, batch):
            month_data = st.session_state.months[mk]
            by_cat = month_data["outflow_df"].groupby("Category")["Amount"].sum().abs()
            mn = by_cat[by_cat.index.isin(needs_cats)].sum()
            mw = by_cat[by_cat.index.isin(wants_cats)].sum()
            ms_explicit = by_cat[by_cat.index.isin(savings_cats)].sum()
            ms = ms_explicit + max(salary - mn - mw - ms_explicit, 0.0)
            col.plotly_chart(
                bucket_bar_fig(mn, mw, ms, month_data["month_label"], show_legend=False),
                use_container_width=True,
            )

    st.divider()

    # Average breakdown
    st.markdown("**Average across all months**")
    all_out    = pd.concat([m["outflow_df"] for m in st.session_state.months.values()])
    n_months   = len(st.session_state.months)
    avg_by_cat = all_out.groupby("Category")["Amount"].sum().abs() / n_months

    actual_needs            = avg_by_cat[avg_by_cat.index.isin(needs_cats)].sum()
    actual_wants            = avg_by_cat[avg_by_cat.index.isin(wants_cats)].sum()
    actual_savings_explicit = avg_by_cat[avg_by_cat.index.isin(savings_cats)].sum()
    actual_savings_leftover = max(salary - actual_needs - actual_wants - actual_savings_explicit, 0.0)
    actual_savings          = actual_savings_explicit + actual_savings_leftover

    left, right = st.columns([1, 2])
    with left:
        st.metric("Needs",   f"£{actual_needs:,.0f}",   delta_str(actual_needs,   ideal_needs))
        st.metric("Wants",   f"£{actual_wants:,.0f}",   delta_str(actual_wants,   ideal_wants))
        st.metric("Savings", f"£{actual_savings:,.0f}", delta_str(actual_savings, ideal_savings))
    with right:
        st.plotly_chart(
            bucket_bar_fig(actual_needs, actual_wants, actual_savings,
                           "Average Monthly Spending vs 50/30/20 Ideal"),
            use_container_width=True,
        )

    st.divider()

    # ── E: Projection Using Actual Net Savings ─────────────────────────────────
    st.subheader("Long-Term Projection — Your Actual Savings Rate")

    st.caption(
        f"Take-home pay **£{salary:,.0f}** − Needs **£{actual_needs:,.0f}** − Wants **£{actual_wants:,.0f}** "
        f"− Savings contributions **£{actual_savings_explicit:,.0f}** "
        f"= leftover **£{actual_savings_leftover:,.0f}**. "
        f"Total saved: **£{actual_savings:,.0f}/month**."
    )

    if actual_savings == 0:
        st.warning(
            "Your Needs, Wants, and Savings spending matches or exceeds your take-home pay — no surplus to project. "
            "Consider reviewing your Wants categories to find areas to reduce."
        )
        return

    st.plotly_chart(
        projection_chart(actual_savings, f"Growth of £{actual_savings:,.0f}/month (your total savings)"),
        use_container_width=True,
    )
    st.dataframe(milestone_table(actual_savings), use_container_width=True)

    st.caption(
        "Figures are illustrative. Past returns do not guarantee future performance. "
        "Always consider your personal tax situation and risk tolerance."
    )
