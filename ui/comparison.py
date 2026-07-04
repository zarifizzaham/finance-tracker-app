import streamlit as st
import pandas as pd
import plotly.express as px


def render_comparison():
    if len(st.session_state.months) < 2:
        st.info("Upload at least 2 months of data to see a comparison.")
        return

    sorted_months = sorted(st.session_state.months.items())

    summary_rows = []
    for _, month in sorted_months:
        out_total = month["outflow_df"]["Amount"].abs().sum()
        inf_total = month["inflow_df"]["Amount"].sum()
        summary_rows.append({
            "Month":    month["month_label"],
            "Outflows": round(out_total, 2),
            "Inflows":  round(inf_total, 2),
            "Net":      round(out_total - inf_total, 2),
        })
    monthly = pd.DataFrame(summary_rows)

    total_spend = monthly["Outflows"].sum()
    avg_spend   = monthly["Outflows"].mean()
    max_row     = monthly.loc[monthly["Outflows"].idxmax()]
    min_row     = monthly.loc[monthly["Outflows"].idxmin()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Spend (All Months)", f"£{total_spend:,.2f}")
    m2.metric("Avg Monthly Spend",        f"£{avg_spend:,.2f}")
    m3.metric("Highest Spend Month", max_row["Month"], delta=f"£{max_row['Outflows']:,.2f}", delta_color="inverse")
    m4.metric("Lowest Spend Month",  min_row["Month"], delta=f"£{min_row['Outflows']:,.2f}", delta_color="inverse")

    st.divider()

    melted = monthly.melt(
        id_vars="Month",
        value_vars=["Outflows", "Inflows", "Net"],
        var_name="Type",
        value_name="Amount",
    )
    fig1 = px.bar(
        melted,
        x="Month", y="Amount", color="Type", barmode="group",
        title="Monthly Overview — Outflows, Inflows & Net",
        text=melted["Amount"].apply(lambda x: f"£{x:,.2f}"),
        template="plotly_dark",
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(
        yaxis_title="Amount (£)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig1, use_container_width=True)

    cat_rows = []
    for _, month in sorted_months:
        for cat, amt in month["outflow_df"].groupby("Category")["Amount"].sum().abs().items():
            cat_rows.append({"Month": month["month_label"], "Category": cat, "Amount": round(amt, 2)})
    cat_df = pd.DataFrame(cat_rows)

    fig2 = px.bar(
        cat_df,
        x="Month", y="Amount", color="Category", barmode="stack",
        title="Spending by Category per Month",
        template="plotly_dark",
    )
    fig2.update_layout(
        yaxis_title="Amount (£)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        top_cats = cat_df.groupby("Category")["Amount"].sum().nlargest(6).index.tolist()
        trend_df = cat_df[cat_df["Category"].isin(top_cats)]
        fig3 = px.line(
            trend_df,
            x="Month", y="Amount", color="Category",
            title="Top Category Trends",
            markers=True,
            template="plotly_dark",
        )
        fig3.update_layout(
            yaxis_title="Amount (£)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        monthly["MoM %"] = monthly["Outflows"].pct_change() * 100
        mom_df = monthly.dropna(subset=["MoM %"])
        fig4 = px.bar(
            mom_df,
            x="Month", y="MoM %",
            title="Month-over-Month Spend Change (%)",
            text=mom_df["MoM %"].apply(lambda x: f"{x:+.1f}%"),
            color="MoM %",
            color_continuous_scale=["#2ecc71", "#e2e2e2", "#e74c3c"],
            color_continuous_midpoint=0,
            template="plotly_dark",
        )
        fig4.update_traces(textposition="outside")
        fig4.update_layout(
            yaxis_title="Change (%)",
            coloraxis_showscale=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)
