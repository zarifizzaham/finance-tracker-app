import streamlit as st
import pandas as pd
import plotly.express as px
from categories import add_keyword_to_category, propagate_category_to_all_months
from persistence import (
    outflow_overrides, inflow_overrides,
    make_tx_key, make_inflow_key,
    save_outflow_overrides, save_inflow_overrides,
)


def render_month(month_key: str):
    
    month = st.session_state.months[month_key]

    # Date range filter — guarded to ±2 days around the detected month
    month_start = pd.to_datetime(month_key).date()
    month_end   = (pd.to_datetime(month_key) + pd.offsets.MonthEnd(0)).date()
    guard_min   = month_start - pd.Timedelta(days=2)
    guard_max   = month_end   + pd.Timedelta(days=2)

    all_dates = [
        pd.to_datetime(d)
        for d in list(month["outflow_df"]["Date"]) + list(month["inflow_df"]["Date"])
    ]
    if not all_dates:
        st.warning("No transactions found in this file.")
        return
    min_date = max(min(all_dates).date(), guard_min)
    max_date = min(max(all_dates).date(), guard_max)

    date_range = st.date_input(
        "Filter by date range",
        value=(min_date, max_date),
        min_value=guard_min,
        max_value=guard_max,
        key=f"dr_{month_key}",
        help="Narrows the transactions shown. Defaults to the full statement period.",
    )

    def _filter(df):
        if len(date_range) == 2:
            s, e = date_range
            return df[(df["Date"] >= s) & (df["Date"] <= e)]
        return df

    out = _filter(month["outflow_df"])
    inf = _filter(month["inflow_df"])

    st.divider()

    sub1, sub2 = st.tabs(["Cash Outflow (Payments)", "Cash Inflow (Transfers In)"])

    # ── Outflow sub-tab ────────────────────────────────────────────────────────
    with sub1:
        st.subheader("Categorise Outflows")
        st.caption("Change categories directly in the table, then click **Apply Changes**.")

        out_msg_key = f"out_msg_{month_key}"
        if out_msg_key in st.session_state:
            n = st.session_state[out_msg_key]
            del st.session_state[out_msg_key]
            if n:
                st.success(f"{n} transaction{'s' if n > 1 else ''} updated.")
            else:
                st.info("No changes detected.")

        out_orig_index = list(out.index)
        out_display    = out[["Date", "Description", "Amount", "Category"]].reset_index(drop=True)

        with st.form(key=f"out_form_{month_key}"):
            edited_outflow = st.data_editor(
                out_display,
                column_config={
                    "Date":     st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Amount":   st.column_config.NumberColumn("Amount", format="£%.2f"),
                    "Category": st.column_config.SelectboxColumn(
                        "Category",
                        options=list(st.session_state.categories.keys()),
                    ),
                },
                disabled=["Date", "Description", "Amount"],
                hide_index=True,
                use_container_width=True,
                key=f"outflow_editor_{month_key}",
            )
            submitted_out = st.form_submit_button("Apply Changes", type="primary")

        if submitted_out:
            changed = 0
            for pos, row in edited_outflow.iterrows():
                real_idx = out_orig_index[pos]
                if row["Category"] == month["outflow_df"].at[real_idx, "Category"]:
                    continue
                month["outflow_df"].at[real_idx, "Category"] = row["Category"]
                add_keyword_to_category(row["Category"], row["Description"])
                propagate_category_to_all_months(row["Description"], row["Category"])
                outflow_overrides[make_tx_key(month["outflow_df"].loc[real_idx])] = row["Category"]
                changed += 1
            if changed:
                save_outflow_overrides()
            st.session_state[out_msg_key] = changed
            st.rerun()

    # ── Inflow sub-tab ─────────────────────────────────────────────────────────
    with sub2:
        st.subheader("Categorise Inflows")
        st.caption(
            "Change categories directly in the table, then click **Apply Changes**. "
            "Each inflow is saved individually so the same description on a different date isn't affected."
        )

        inf_msg_key = f"inf_msg_{month_key}"
        if inf_msg_key in st.session_state:
            n = st.session_state[inf_msg_key]
            del st.session_state[inf_msg_key]
            if n:
                st.success(f"{n} transaction{'s' if n > 1 else ''} updated.")
            else:
                st.info("No changes detected.")

        inf_orig_index = list(inf.index)
        inf_display    = inf[["Date", "Description", "Amount", "Category"]].reset_index(drop=True)

        with st.form(key=f"inf_form_{month_key}"):
            edited_inflow = st.data_editor(
                inf_display,
                column_config={
                    "Date":     st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Amount":   st.column_config.NumberColumn("Amount", format="£%.2f"),
                    "Category": st.column_config.SelectboxColumn(
                        "Category",
                        options=list(st.session_state.categories.keys()),
                    ),
                },
                disabled=["Date", "Description", "Amount"],
                hide_index=True,
                use_container_width=True,
                key=f"inflow_editor_{month_key}",
            )
            submitted_inf = st.form_submit_button("Apply Changes", type="primary")

        if submitted_inf:
            changed = 0
            for pos, row in edited_inflow.iterrows():
                real_idx = inf_orig_index[pos]
                if row["Category"] == month["inflow_df"].at[real_idx, "Category"]:
                    continue
                month["inflow_df"].at[real_idx, "Category"] = row["Category"]
                inflow_overrides[make_inflow_key(month["inflow_df"].loc[real_idx])] = row["Category"]
                changed += 1
            save_inflow_overrides()
            st.session_state[inf_msg_key] = changed
            st.rerun()

    # ── Expense summary & charts ───────────────────────────────────────────────
    # Re-filter after handlers so Apply Changes is reflected without a second rerun
    out = _filter(month["outflow_df"])
    inf = _filter(month["inflow_df"])

    st.subheader("Expense Summary")

    outflow_totals = out.groupby("Category")["Amount"].sum().abs().reset_index()
    outflow_totals.columns = ["Category", "Outflows"]

    outflow_counts = out.groupby("Category")["Amount"].count().reset_index()
    outflow_counts.columns = ["Category", "Quantity"]

    inflow_totals = inf.groupby("Category")["Amount"].sum().reset_index()
    inflow_totals.columns = ["Category", "Inflows"]

    category_totals = outflow_totals.merge(outflow_counts, on="Category", how="left").fillna(0)
    category_totals = category_totals.merge(inflow_totals, on="Category", how="outer").fillna(0)
    category_totals["Expenses"] = category_totals["Outflows"] - category_totals["Inflows"]
    category_totals["Quantity"] = category_totals["Quantity"].astype(int)
    category_totals = category_totals[["Category", "Quantity", "Outflows", "Inflows", "Expenses"]]
    category_totals = category_totals.sort_values("Expenses", ascending=False)

    st.dataframe(
        category_totals,
        column_config={
            "Quantity": st.column_config.NumberColumn("Quantity", format="%d"),
            "Outflows": st.column_config.NumberColumn("Outflows", format="%.2f"),
            "Inflows":  st.column_config.NumberColumn("Inflows",  format="%.2f"),
            "Expenses": st.column_config.NumberColumn("Expenses", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        fig = px.pie(
            category_totals[category_totals["Expenses"] > 0],
            values="Expenses",
            names="Category",
            title="Expenses by Category",
            hole=0.35,
            template="plotly_dark",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=14)
        fig.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=14),
            title_font_size=16,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each slice shows one spending category as a percentage of your total outflows for the period. Hover over a slice to see the exact amount.")

    with chart_col2:
        avg_data = category_totals[category_totals["Quantity"] > 0].copy()
        avg_data["Average"] = avg_data["Outflows"] / avg_data["Quantity"]
        avg_data = avg_data.sort_values("Average", ascending=True)
        fig_bar = px.bar(
            avg_data,
            x="Average",
            y="Category",
            orientation="h",
            title="Average Expense per Category",
            text=avg_data["Average"].apply(lambda x: f"£{x:.2f}"),
            template="plotly_dark",
        )
        fig_bar.update_traces(textposition="outside", textfont_size=13)
        fig_bar.update_layout(
            xaxis_title="Amount (£)",
            yaxis_title="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=14),
            title_font_size=16,
            xaxis=dict(tickfont=dict(size=13)),
            yaxis=dict(tickfont=dict(size=13)),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("The average amount spent per individual transaction in each category. A high average means fewer but larger purchases; a low average means many small ones.")

    total_expense = out["Amount"].abs().sum()
    total_inflows = inf["Amount"].sum()
    net_total     = total_expense - total_inflows

    per_category = category_totals.rename(columns={"Expenses": "Net Total"})
    summary_row  = pd.DataFrame([{
        "Category":  "TOTAL",
        "Outflows":  total_expense,
        "Inflows":   total_inflows,
        "Net Total": net_total,
    }])
    bar_source = pd.concat(
        [per_category[["Category", "Outflows", "Inflows", "Net Total"]], summary_row],
        ignore_index=True,
    )
    bar_melted = bar_source.melt(
        id_vars="Category",
        value_vars=["Outflows", "Inflows", "Net Total"],
        var_name="Type",
        value_name="Amount",
    )
    fig2 = px.bar(
        bar_melted,
        x="Category",
        y="Amount",
        color="Type",
        barmode="group",
        title="Outflows, Inflows & Net Total by Category",
        text=bar_melted["Amount"].apply(lambda x: f"£{x:.2f}"),
        template="plotly_dark",
    )
    fig2.update_traces(textposition="outside", textfont_size=13)
    fig2.update_layout(
        yaxis_title="Amount (£)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        title_font_size=16,
        xaxis=dict(tickfont=dict(size=13)),
        yaxis=dict(tickfont=dict(size=13)),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Side-by-side comparison of total money out (Outflows), money in (Inflows), and the net difference per category. A negative Net Total means more came in than went out — common for Transfers. The TOTAL column summarises the entire month.")
