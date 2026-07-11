import io
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from fpdf import FPDF

PAGE_W = 180  # effective page width in mm (A4 210mm - 2 × 15mm margins)


def _safe(text: str) -> str:
    """Sanitise text for Helvetica (Latin-1 only). Replaces em/en dashes and drops other non-Latin-1 chars."""
    return (
        str(text)
        .replace("—", "-")   # em dash —
        .replace("–", "-")   # en dash –
        .replace("’", "'")   # right single quote '
        .replace("‘", "'")   # left single quote '
        .replace("×", "x")   # multiplication sign ×
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


# ── Rendering helpers ──────────────────────────────────────────────────────────

def _fig_png(fig, width=900, height=400):
    """Render a Plotly figure to PNG bytes via kaleido. Returns None on failure."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=1.5)
    except Exception:
        return None


def _embed_fig(pdf: FPDF, fig, height=400):
    img = _fig_png(fig, width=int(PAGE_W * 3.78), height=height)
    if img:
        pdf.image(io.BytesIO(img), w=PAGE_W)
    pdf.ln(4)


def _section_header(pdf: FPDF, text: str):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, _safe(f"  {text}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)


def _sub_header(pdf: FPDF, text: str):
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _table_header(pdf: FPDF, headers: list, widths: list):
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _safe(h), border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _table_row(pdf: FPDF, values: list, widths: list, stripe: bool):
    pdf.set_font("Helvetica", "", 7)
    pdf.set_fill_color(242, 242, 242)
    for val, w in zip(values, widths):
        pdf.cell(w, 5, _safe(val), border="LRB", fill=stripe)
    pdf.ln()


# Explicit color maps so kaleido renders colour instead of black
_TYPE_COLORS     = {"Outflows": "#636efa", "Inflows": "#00cc96", "Net": "#ef553b"}
_SCENARIO_COLORS = {"Cash (0%)": "#aec7e8", "Savings (3%)": "#1f77b4", "Index (7%)": "#d62728"}
_CAT_SEQ         = px.colors.qualitative.Plotly  # 10 distinct colours


def _white_layout():
    # template="plotly" ensures the default coloured theme; explicit bg/font overrides it
    return dict(template="plotly", paper_bgcolor="white", plot_bgcolor="white", font_color="black")


# ── Main report builder ────────────────────────────────────────────────────────

def generate_report_pdf(salary: float, needs_cats: list, wants_cats: list, savings_cats: list) -> bytes:
    months = st.session_state.months
    sorted_keys = sorted(months.keys())
    today = date.today()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)

    # ── Cover ──────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(20)
    pdf.cell(0, 14, "Finance Dashboard Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 9, f"{today.day} {today.strftime('%B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)

    all_banks = sorted({b for m in months.values() for b in m["banks"]})
    total_tx  = sum(len(m["outflow_df"]) + len(m["inflow_df"]) for m in months.values())
    pdf.set_font("Helvetica", "", 10)
    for line in [
        f"Banks:                 {', '.join(all_banks)}",
        f"Months:                {', '.join(months[mk]['month_label'] for mk in sorted_keys)}",
        f"Total transactions:    {total_tx}",
        f"Monthly take-home:     GBP {salary:,.0f}",
        f"Needs categories:      {', '.join(needs_cats) or 'None'}",
        f"Wants categories:      {', '.join(wants_cats) or 'None'}",
        f"Savings categories:    {', '.join(savings_cats) or 'None'}",
    ]:
        pdf.cell(0, 7, _safe(line), new_x="LMARGIN", new_y="NEXT")

    # ── Section 1: Full transaction log ───────────────────────────────────────
    pdf.add_page()
    _section_header(pdf, "Section 1 — Full Transaction Log")

    rows = []
    for mk in sorted_keys:
        out = months[mk]["outflow_df"].copy(); out["Type"] = "Outflow"
        inf = months[mk]["inflow_df"].copy();  inf["Type"] = "Inflow"
        rows.extend([out, inf])
    all_tx = pd.concat(rows, ignore_index=True).sort_values("Date").reset_index(drop=True)

    _table_header(pdf, ["Date", "Description", "Amount (£)", "Category", "Type"], [24, 78, 24, 36, 18])
    for i, row in all_tx.iterrows():
        _table_row(pdf, [
            str(row["Date"]),
            str(row["Description"])[:36],
            f"{row['Amount']:.2f}",
            str(row["Category"])[:20],
            row["Type"],
        ], [24, 78, 24, 36, 18], stripe=i % 2 == 0)

    # ── Section 2: Per-month expense summaries ────────────────────────────────
    for mk in sorted_keys:
        pdf.add_page()
        m = months[mk]
        _section_header(pdf, f"Section 2 — {m['month_label']} Expense Summary")

        out = m["outflow_df"]
        inf = m["inflow_df"]
        out_t = out.groupby("Category")["Amount"].sum().abs().reset_index()
        out_t.columns = ["Category", "Outflows"]
        inf_t = inf.groupby("Category")["Amount"].sum().reset_index()
        inf_t.columns = ["Category", "Inflows"]
        summary = out_t.merge(inf_t, on="Category", how="outer").fillna(0)
        summary["Net"] = summary["Outflows"] - summary["Inflows"]
        summary = summary.sort_values("Outflows", ascending=False).reset_index(drop=True)

        _table_header(pdf, ["Category", "Outflows (£)", "Inflows (£)", "Net (£)"], [60, 40, 40, 40])
        for i, row in summary.iterrows():
            _table_row(pdf, [
                str(row["Category"])[:28],
                f"{row['Outflows']:.2f}",
                f"{row['Inflows']:.2f}",
                f"{row['Net']:.2f}",
            ], [60, 40, 40, 40], stripe=i % 2 == 0)
        pdf.ln(4)

        pie_data = summary[summary["Outflows"] > 0]
        if not pie_data.empty:
            fig_pie = px.pie(
                pie_data, values="Outflows", names="Category",
                title=f"Expenses by Category — {m['month_label']}", hole=0.35,
                color_discrete_sequence=_CAT_SEQ,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(showlegend=False, **_white_layout())
            _embed_fig(pdf, fig_pie, height=380)

        bar_melted = summary.melt(
            id_vars="Category", value_vars=["Outflows", "Inflows", "Net"],
            var_name="Type", value_name="Amount",
        )
        fig_bar = px.bar(
            bar_melted, x="Category", y="Amount", color="Type", barmode="group",
            title=f"Outflows, Inflows & Net — {m['month_label']}",
            color_discrete_map=_TYPE_COLORS,
        )
        fig_bar.update_layout(yaxis_title="Amount (£)", **_white_layout())
        _embed_fig(pdf, fig_bar, height=380)

    # ── Section 3: Month comparison ───────────────────────────────────────────
    pdf.add_page()
    _section_header(pdf, "Section 3 — Month Comparison")

    cmp_rows = []
    for mk in sorted_keys:
        m  = months[mk]
        ot = m["outflow_df"]["Amount"].abs().sum()
        it = m["inflow_df"]["Amount"].sum()
        cmp_rows.append({"Month": m["month_label"], "Outflows": round(ot, 2),
                         "Inflows": round(it, 2), "Net": round(ot - it, 2)})
    monthly_df = pd.DataFrame(cmp_rows)

    _table_header(pdf, ["Month", "Outflows (£)", "Inflows (£)", "Net (£)"], [50, 43, 43, 44])
    for i, row in monthly_df.iterrows():
        _table_row(pdf, [row["Month"], f"{row['Outflows']:.2f}",
                         f"{row['Inflows']:.2f}", f"{row['Net']:.2f}"],
                   [50, 43, 43, 44], stripe=i % 2 == 0)
    pdf.ln(4)

    if len(sorted_keys) >= 2:
        melted = monthly_df.melt(id_vars="Month", value_vars=["Outflows", "Inflows", "Net"],
                                  var_name="Type", value_name="Amount")
        fig_cmp = px.bar(melted, x="Month", y="Amount", color="Type", barmode="group",
                         title="Monthly Overview — Outflows, Inflows & Net",
                         color_discrete_map=_TYPE_COLORS)
        fig_cmp.update_layout(yaxis_title="Amount (£)", **_white_layout())
        _embed_fig(pdf, fig_cmp, height=380)

        cat_rows = []
        for mk in sorted_keys:
            for cat, amt in months[mk]["outflow_df"].groupby("Category")["Amount"].sum().abs().items():
                cat_rows.append({"Month": months[mk]["month_label"], "Category": cat, "Amount": round(amt, 2)})
        cat_df   = pd.DataFrame(cat_rows)
        top_cats = cat_df.groupby("Category")["Amount"].sum().nlargest(6).index.tolist()
        fig_trend = px.line(cat_df[cat_df["Category"].isin(top_cats)],
                            x="Month", y="Amount", color="Category",
                            title="Top Category Trends", markers=True,
                            color_discrete_sequence=_CAT_SEQ)
        fig_trend.update_layout(yaxis_title="Amount (£)", **_white_layout())
        _embed_fig(pdf, fig_trend, height=350)

    # ── Section 4: 50/30/20 analysis ──────────────────────────────────────────
    pdf.add_page()
    _section_header(pdf, "Section 4 — 50/30/20 Savings Analysis")

    ideal_needs   = salary * 0.50
    ideal_wants   = salary * 0.30
    ideal_savings = salary * 0.20

    all_out    = pd.concat([m["outflow_df"] for m in months.values()])
    n_months   = len(months)
    avg_by_cat = all_out.groupby("Category")["Amount"].sum().abs() / n_months

    actual_needs    = avg_by_cat[avg_by_cat.index.isin(needs_cats)].sum()
    actual_wants    = avg_by_cat[avg_by_cat.index.isin(wants_cats)].sum()
    actual_sav_exp  = avg_by_cat[avg_by_cat.index.isin(savings_cats)].sum()
    actual_sav_left = max(salary - actual_needs - actual_wants - actual_sav_exp, 0.0)
    actual_savings  = actual_sav_exp + actual_sav_left

    _table_header(pdf, ["Bucket", "Actual (£)", "Target (£)", "Difference (£)"], [45, 45, 45, 45])
    for i, (bucket, actual, ideal) in enumerate([
        ("Needs",   actual_needs,   ideal_needs),
        ("Wants",   actual_wants,   ideal_wants),
        ("Savings", actual_savings, ideal_savings),
    ]):
        _table_row(pdf, [bucket, f"{actual:,.0f}", f"{ideal:,.0f}", f"{actual - ideal:+,.0f}"],
                   [45, 45, 45, 45], stripe=i % 2 == 0)
    pdf.ln(4)

    fig_bkt = px.bar(
        pd.DataFrame({
            "Bucket":     ["Needs", "Wants", "Savings"] * 2,
            "Type":       ["Actual"] * 3 + ["Target"] * 3,
            "Amount (£)": [actual_needs, actual_wants, actual_savings,
                           ideal_needs,  ideal_wants,  ideal_savings],
        }),
        x="Bucket", y="Amount (£)", color="Type", barmode="group",
        title="Average Monthly Spending vs 50/30/20 Target",
        color_discrete_map={"Actual": "#636efa", "Target": "#00cc96"},
    )
    fig_bkt.update_layout(**_white_layout())
    _embed_fig(pdf, fig_bkt, height=360)

    # Savings projection
    _sub_header(pdf, f"Savings Projection — £{actual_savings:,.0f}/month")

    SCENARIOS  = {"Cash (0%)": 0.00, "Savings (3%)": 0.03, "Index (7%)": 0.07}
    MILESTONES = {1: 12, 5: 60, 10: 120, 20: 240, 40: 480}

    def fv(pmt, r_annual, n):
        if pmt == 0: return 0.0
        if r_annual == 0: return float(pmt * n)
        r = r_annual / 12
        return pmt * ((1 + r) ** n - 1) / r

    proj_rows = [
        {"Month": n, "Scenario": label, "Value (£)": fv(actual_savings, rate, n)}
        for n in range(1, 481)
        for label, rate in SCENARIOS.items()
    ]
    fig_proj = px.line(pd.DataFrame(proj_rows), x="Month", y="Value (£)", color="Scenario",
                       title=f"Growth of £{actual_savings:,.0f}/month over 40 years",
                       color_discrete_map=_SCENARIO_COLORS)
    for yrs, m_n in MILESTONES.items():
        fig_proj.add_vline(x=m_n, line_dash="dot", line_color="rgba(100,100,100,0.5)",
                           annotation_text=f"{yrs}yr", annotation_position="top left",
                           annotation_font_size=9)
    fig_proj.update_layout(**_white_layout())
    _embed_fig(pdf, fig_proj, height=380)

    # Milestone table
    _sub_header(pdf, "Milestone Summary")
    ms_headers = ["Scenario"] + [f"{y} yr" for y in MILESTONES]
    ms_widths  = [50] + [26] * len(MILESTONES)
    _table_header(pdf, ms_headers, ms_widths)
    for i, (label, rate) in enumerate(SCENARIOS.items()):
        row_vals = [label] + [f"£{fv(actual_savings, rate, m_n):,.0f}" for m_n in MILESTONES.values()]
        _table_row(pdf, row_vals, ms_widths, stripe=i % 2 == 0)

    return bytes(pdf.output())
