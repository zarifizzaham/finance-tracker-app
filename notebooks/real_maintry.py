import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os
import base64 # encodes the background image as a string for CSS

st.set_page_config(page_title="Simple Finance Tracking App", page_icon="🤑", layout='wide')

def get_base64_image(path):
    with open(path, "rb") as f:          # open in binary read mode
        return base64.b64encode(f.read()).decode()  # bytes → base64 text

img = get_base64_image("image finance tracker.webp")
# img is now a very long string like "UklGRv4AAABXRUJQVlA4..."

st.markdown(f"""
<style>
.stApp {{
    background-image: url("data:image/webp;base64,{img}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stAppViewContainer"] {{
    background: rgba(0, 0, 0, 0.30);   /* dark overlay on the whole app */
}}
.block-container {{
    background: rgba(14, 17, 23, 0.55); /* frosted card on the main content */
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    padding: 2rem 3rem !important;
}}
[data-testid="stHeader"] {{
    background: rgba(0, 0, 0, 0.0);    /* transparent top bar */
}}
</style>
""", unsafe_allow_html=True)

def make_fingerprint(columns):
    return ",".join(sorted(c).strip() for c in columns)
# The string whose method is called is inserted in between each given string.
# The result is returned as a new string.

def detect_bank(columns):
    col_set = set(columns)  # set lookup is O(1), faster than list lookup
    if "Started Date" in col_set and "Completed Date" in col_set:
        return "Revolut"
    if "Emoji" in col_set and "Name" in col_set:
        return "Monzo"
    if "Memo" in col_set and "Subcategory" in col_set:
        return "Barclays"
    if "Paid out" in col_set and "Paid in" in col_set:
        return "HSBC"
    if "Counter Party" in col_set and "Reference" in col_set:
        return "Starling"
    return None  # unknown bank

def load_bank_mappings():
    if os.path.exists("bank_mappings.json"):
        with open("bank_mappings.json","r") as f:
            return json.load(f)
    return {}

def save_bank_mappings(mappings):
    with open("bank_mappings.json") as f:
        json.dump(mappings,f, indent=2) # Same data, just formatted.

def categorize_transactions(df):
    df["Category"] = "Uncategorized"  # default for every row

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue  # nothing to match against

        lowered_keywords = [kw.lower().strip() for kw in keywords]

        for idx, row in df.iterrows():
            if row["Amount"] > 0:
                continue  # skip inflows
            if row["Description"].lower().strip() in lowered_keywords:
                df.at[idx, "Category"] = category
                # .at[idx, col] is the fastest way to set a single cell by index

    return df

def save_categories():
    with open("categories.json", "w") as f:
        json.dump(st.session_state.categories, f)

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()  # write to disk immediately
        return True
    return False  # already exists — no duplicate

# Initialises with defaults only if session state is empty
if "categories" not in st.session_state:
    st.session_state.categories = {"Uncategorized": [], "New category": []}

# Overwrite with saved data every rerun - JSON is the source of truth
if os.path.exists("categories.json"):
    with open("categories.json", "r") as f:
        st.session_state.categories = json.load(f)

# Loads saved overrides at startup
if os.path.exists("inflow_overrides.json"):
    with open("inflow_categories.json","r") as f:
        inflow_overrides = json.load(f)

def make_inflow_key(row):
    return f"{row['Date']}|{row['Description']}|{row['Amount']}"

def apply_inflow_overrides(df):
    # Called once when a CSV is first loaded - restores previously saved categories
    for idx, row in df.iterrows():
        key = make_inflow_key(row)
        if key in inflow_overrides:
            df.at[idx,"Category"] = inflow_overrides[key]
    return df

def save_inflow_overrides():
    with open("inflow_overrides.json","w") as f:
        json.dump(inflow_overrides,f)

def normalise_df(df, fmt):
    df = df.copy()  # never modify the original

    # ── Date ──────────────────────────────────────────────────────────────────
    # Try the stored format string first.
    # If the bank changed its export format (e.g. Revolut switched date style),
    # fall back to 'mixed' which lets pandas infer the format per row.
    try:
        df["Date"] = pd.to_datetime(df[fmt["date_col"]], format=fmt["date_format"]).dt.date
    except ValueError:
        df["Date"] = pd.to_datetime(df[fmt["date_col"]], format="mixed", dayfirst=True).dt.date
    # .dt.date strips the time component, giving a plain date object (2026-05-01)

    # ── Description ───────────────────────────────────────────────────────────
    df["Description"] = df[fmt["description_col"]].astype(str).str.strip()

    # ── Amount ────────────────────────────────────────────────────────────────
    if "debit_col" in fmt and "credit_col" in fmt:
        # Banks like HSBC split payments and receipts into two columns.
        # Debit = money out (positive number), Credit = money in (positive number).
        # We convert to: negative = outflow, positive = inflow.
        debit  = pd.to_numeric(df[fmt["debit_col"]].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        credit = pd.to_numeric(df[fmt["credit_col"]].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["Amount"] = credit - debit  # credit positive, debit negative
    else:
        # Most banks use a single signed amount column.
        # .str.replace(",", "") handles amounts like "1,234.56"
        # errors="coerce" turns unparseable values into NaN instead of crashing
        df["Amount"] = pd.to_numeric(df[fmt["amount_col"]].astype(str).str.replace(",", ""), errors="coerce")

    # Keep only the three standard columns and drop rows with no amount
    return df[["Date", "Description", "Amount"]].dropna(subset=["Amount"])

def load_transactions(file, fmt):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]  # remove accidental whitespace
        df = normalise_df(df, fmt)
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None  # caller must check for None
   
# 7c - get_month_info
# Uses the most frequent month across all dates rather than first date
def get_month_info(df):
    dominant = pd.to_datetime(df["Date"]).dt.to_period("M").value_counts().idxmax()
    dt = dominant.to_timestamp() # Period -> Timestamp so we can use strftime
    return dt.strftime("%Y-%m"), dt.strftime("%B %Y")
    # Returns ("2026-05","May 2026")

# Section 8 - Session State for Months 
if "months" not in st.session_state:
    st.session_state.months = {}

# Section 9 - Column Mapping UI (Unknown Banks)

DATE_FORMAT_OPTIONS = {
    "dd/mm/YYYY HH:MM  (e.g. 01/06/2026 14:30)": "%d/%m/%Y %H:%M",
    "dd/mm/YYYY        (e.g. 01/06/2026)":        "%d/%m/%Y",
    "YYYY-MM-DD        (e.g. 2026-06-01)":        "%Y-%m-%d",
    "mm/dd/YYYY        (e.g. 06/01/2026)":        "%m/%d/%Y",
    "dd-mm-YYYY        (e.g. 01-06-2026)":        "%d-%m-%Y",
    "dd MMM YYYY       (e.g. 01 Jun 2026)":       "%d %b %Y",
}

def show_mapping_ui(raw_df, suffix=""):
    st.warning("Bank format not recognised. Map your columns below.")
    st.dataframe(raw_df.head(3), use_container_width=True, hide_index=True)

    cols = list(raw_df.columns)
    c1, c2, c3, c4 = st.columns(4)

    # Each selectbox gets a unique key by including the filename as suffix
    date_col   = c1.selectbox("Date column",        cols, key=f"map_date_{suffix}")
    desc_col   = c2.selectbox("Description column", cols, key=f"map_desc_{suffix}")
    amount_col = c3.selectbox("Amount column",      cols, key=f"map_amount_{suffix}")
    fmt_label  = c4.selectbox("Date format",        list(DATE_FORMAT_OPTIONS.keys()), key=f"map_fmt_{suffix}")

    if st.button("Save & Continue", type="primary", key=f"map_btn_{suffix}"):
        return {
            "date_col":        date_col,
            "date_format":     DATE_FORMAT_OPTIONS[fmt_label],
            "description_col": desc_col,
            "amount_col":      amount_col,
        }
    return None  # user hasn't clicked Save yet

# Section 10 - render_month: Per-Month Tab Content
def render_month(month_key):
    month = st.session_state.months[month_key]

    # Derives the hard boundaries for this calendar month
    month_start = pd.to_datetime(month_key).date()
    month_end = (pd.to_datetime(month_key) + pd.offsets.MonthEnd(0)).date()
    guard_min = month_start - pd.Timedelta(days=2)
    guard_max = month_end + pd.Timedelta(days=2)

    # Finds th actual min/max dates from the data, clamped to the guard
    all_dates = [pd.to_datetime(d) for d in list(month['outflow_df']['Date'])+ list(month['inflow_df']['Date'])]
    min_date = max(min(all_dates).date(), guard_min) # can't go before guard_min
    max_date = min(max(all_dates).date(), guard_max) # can't go after guard_max

    date_range = st.date_input(
        "Select date range",
        value=(min_date, max_date), # default = full data range
        min_value = guard_min,      # user cannot pick before this
        max_value = guard_max,      # user cannot pick after this
        key=f"dr_{month_key}",
    )

    if len(date_range) == 2:
        s, e = date_range
        out = month['outflow_df'][(month['outflow_df']['Date'] >= s) & (month['outflow_df']['Date'] <= e)]
        inf = month['inflow_df'][(month['inflow_df']['Date'] >= s) & (month['inflow_df']['Date'] <= e)]
    else: # user cleared the first datee - avoid crash 
        out = month['outflow_df']
        inf = month['inflow_df']
    
# 10b - Data editor and Apply Changes

    sub1, sub2 = st.tabs(["Cash Outflow (Payments)", "Cash Inflow (Transfers In)"])

    with sub1:
        st.subheader("Categorise Outflows")
        st.caption("Click a row in the Category column, choose from the dropdown, then hit Apply Changes.")

        edited_outflow = st.data_editor(
            out[["Date", "Description", "Amount", "Category"]],
            column_config={
                "Date":     st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Amount":   st.column_config.NumberColumn("Amount", format="%.2f"),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(st.session_state.categories.keys())
                ),
            },
            hide_index=True,
            use_container_width=True,
            key=f"outflow_editor_{month_key}",
        )

        if st.button("Apply Changes", type="primary", key=f"apply_out_{month_key}"):
            for idx, row in edited_outflow.iterrows():
                # Only process rows the user actually changed
                if row['Category'] == month["outflow_df"].at[idx, "Category"]:
                    continue
                # Update the stored DataFrame
                month['outflow_df'].at[idx,"Category"] = row["Category"]
                # Save the description as a keyword so future uploads auto-categorised
                add_keyword_to_category(row["Category"], row["Description"])

    with sub2:
        st.subheader("Categorise Inflows")
        edited_inflow = st.data_editor(
            inf[["Date", "Description", "Amount", "Category"]],
            column_config={
                "Date":     st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Amount":   st.column_config.NumberColumn("Amount", format="%.2f"),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(st.session_state.categories.keys())
                ),
            },
            hide_index=True,
            use_container_width=True,
            key=f"inflow_editor_{month_key}",
        )

        if st.button("Apply Changes", type="primary", key=f"apply_inf_{month_key}"):
            for idx, row in edited_inflow.iterrows():
                month["inflow_df"].at[idx, "Category"] = row["Category"]
                inflow_overrides[make_inflow_key(row)] = row["Category"]  # save per-transaction
            save_inflow_overrides()


# section 10c - Expense summary and charts

    if len(date_range == 2):
        s, e = date_range
        out = month["outflow_df"][(month["outflow_df"]["Date"] >= s) & (month["outflow_df"]["Date"] <= e)]
        inf = month["inflow_df"] [(month["inflow_df"]["Date"]  >= s) & (month["inflow_df"]["Date"]  <= e)]
    else:
        out = month["outflow_df"]
        inf = month["inflow_df"]
    
    st.subheader("Expense Summary")

    outflow_totals = out.groupby("Category")["Amount"].sum().abs().reset_index()
    outflow_totals.columns = ["Category","Outflows"]
    # reset_index() converts the groupby result back to a regular DataFrame
    # with Category as a nrmal column instead of the index

    outflow_counts = out.groupby("Category")["Amount"].count().reset_index()
    outflow_counts.columns = ['Category','Quantity']

    inflow_totals = inf.groupby("Category")["Amount"].sum().reset_index()
    inflow_totals.columns = ["Category","Inflows"]

    # Merging all three into one summary table
    category_totals = outflow_totals.merge(outflow_counts, on="Category",how = "left")
    category_totals = inflow_totals.merge(category_totals, on="Category",how='outer').fillna(0)
    category_totals["Expenses"] = category_totals['Outflows'] - category_totals["Inflows"]
    category_totals["Quantity"] = category_totals["Quantity"].astype(int)
    category_totals = category_totals[["Category","Quantity","Outflows","Inflows","Expenses"]]
    category_totals = category_totals.sort_values("Expenses",ascending=False)


# Section 10d - Charts

    chart_col1, chart_col2 = st.columns(2) # side-by-side layout

    with chart_col1:
        fig = px.pie(
            category_totals[category_totals["Expenses"] > 0],
            values="Expenses",
            names="Category",
            title="Expenses by Category",
            hole = 0.35,
            template = "plotly_dark",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        avg_data = category_totals[category_totals["Quantity"]>0].copy()
        avg_data["Average"] = avg_data["Outflows"]/avg_data["Quantity"]
        avg_data = avg_data.sort_values("Average",ascending=True) # largest at top
        fig_bar = px.bar(
            avg_data,
            x="Average", y="Category",
            orientation="h",
            title="Average Expense per Category",
            text=avg_data["Average"].apply(lambda x: f"£{x:.2f}"),
            template="plotly_dark",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(xaxis_title="Amount (£)", yaxis_title="",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Grouped bar: Outflows / Inflows / Net per category
    total_expense = out["Amount"].abs().sum()
    total_inflows = inf["Amount"].sum()
    net_total     = total_expense - total_inflows

    per_category = category_totals.rename(columns={"Expenses": "Net Total"})
    summary_row  = pd.DataFrame([{"Category": "TOTAL", "Outflows": total_expense,
                                   "Inflows": total_inflows, "Net Total": net_total}])

    bar_source = pd.concat([per_category[["Category", "Outflows", "Inflows", "Net Total"]], summary_row],
                            ignore_index=True)

    # melt: wide → long format for grouped bar
    bar_melted = bar_source.melt(
        id_vars="Category",
        value_vars=["Outflows", "Inflows", "Net Total"],
        var_name="Type",
        value_name="Amount",
    )

    fig2 = px.bar(bar_melted, x="Category", y="Amount", color="Type", barmode="group",
                  title="Outflows, Inflows & Net Total by Category",
                  text=bar_melted["Amount"].apply(lambda x: f"£{x:.2f}"),
                  template="plotly_dark")
    fig2.update_traces(textposition="outside")
    fig2.update_layout(yaxis_title="Amount (£)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)


# Section 11 - render_comparison: Multi-Month Analysis

def render_comparison():
    if len(st.session_state.months) < 2:
        st.info("Upload at least 2 months of data to see a comparison.")
        return

    sorted_months = sorted(st.session_state.months.items())  # chronological order

    # ── Monthly totals ─────────────────────────────────────────────────────────
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

    # ── Key metric cards ───────────────────────────────────────────────────────
    # st.metric shows a headline number with an optional delta below it
    total_spend = monthly["Outflows"].sum()
    avg_spend   = monthly["Outflows"].mean()
    max_row     = monthly.loc[monthly["Outflows"].idxmax()]
    min_row     = monthly.loc[monthly["Outflows"].idxmin()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Spend (All Months)", f"£{total_spend:,.2f}")
    m2.metric("Avg Monthly Spend",        f"£{avg_spend:,.2f}")
    m3.metric("Highest Spend Month",      max_row["Month"],
              delta=f"£{max_row['Outflows']:,.2f}", delta_color="inverse")  # red = high spend
    m4.metric("Lowest Spend Month",       min_row["Month"],
              delta=f"£{min_row['Outflows']:,.2f}", delta_color="inverse")

    st.divider()

    # ── Chart 1: Monthly overview grouped bar ──────────────────────────────────
    melted = monthly.melt(id_vars="Month", value_vars=["Outflows", "Inflows", "Net"],
                          var_name="Type", value_name="Amount")
    fig1 = px.bar(melted, x="Month", y="Amount", color="Type", barmode="group",
                  title="Monthly Overview — Outflows, Inflows & Net",
                  text=melted["Amount"].apply(lambda x: f"£{x:,.2f}"),
                  template="plotly_dark")
    fig1.update_traces(textposition="outside")
    fig1.update_layout(yaxis_title="Amount (£)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: Category spend per month stacked bar ─────────────────────────
    cat_rows = []
    for _, month in sorted_months:
        for cat, amt in month["outflow_df"].groupby("Category")["Amount"].sum().abs().items():
            cat_rows.append({"Month": month["month_label"], "Category": cat, "Amount": round(amt, 2)})
    cat_df = pd.DataFrame(cat_rows)

    fig2 = px.bar(cat_df, x="Month", y="Amount", color="Category", barmode="stack",
                  title="Spending by Category per Month", template="plotly_dark")
    fig2.update_layout(yaxis_title="Amount (£)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # ── Chart 3: Top category trends line chart ────────────────────────────
        top_cats = cat_df.groupby("Category")["Amount"].sum().nlargest(6).index.tolist()
        # nlargest(6) finds the 6 categories with highest total spend across all months
        trend_df = cat_df[cat_df["Category"].isin(top_cats)]
        fig3 = px.line(trend_df, x="Month", y="Amount", color="Category",
                       title="Top Category Trends", markers=True, template="plotly_dark")
        fig3.update_layout(yaxis_title="Amount (£)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        # ── Chart 4: Month-over-month % change ────────────────────────────────
        monthly["MoM %"] = monthly["Outflows"].pct_change() * 100
        # pct_change() computes (current - previous) / previous
        # The first row is always NaN (no previous month to compare to)
        mom_df = monthly.dropna(subset=["MoM %"])

        fig4 = px.bar(mom_df, x="Month", y="MoM %",
                      title="Month-over-Month Spend Change (%)",
                      text=mom_df["MoM %"].apply(lambda x: f"{x:+.1f}%"),
                      color="MoM %",
                      color_continuous_scale=["#2ecc71", "#e2e2e2", "#e74c3c"],
                      color_continuous_midpoint=0,  # 0% = white, negative = green, positive = red
                      template="plotly_dark")
        fig4.update_traces(textposition="outside")
        fig4.update_layout(yaxis_title="Change (%)", coloraxis_showscale=False,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)


def main():
    st.title("Simple Finance Dashboard")

    # accept_multiple_files=True returns a list of file objects
    uploaded_files = st.file_uploader(
        "Upload your transaction CSV files (one per month)",
        type = ["csv"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.session_state.months = {} # clear everything if no files
        return
    # practical reason: if you didnt clear it, when user has removed old files,
    # old data will still be there 

    # - Step 2: Remove months for deselected files ----------------
    current_names = {f.name for f in uploaded_files}

    for mk in list(st.session_state.months.keys()):
        # list() is required - you can't delete from a dict while iterating it
        if st.session_state.months[mk]["filename"] not in current_names:
            del st.session_state.months[mk]

    # - Step 3: Process new files ---------------------------------

    bank_mappings = load_bank_mappings()
    processed_names = {v['filename'] for v in st.session_state.months.values()}

    for uploaded_file in uploaded_files:
        if uploaded_file.name in processed_names:
            continue # already processed on a prev rerun - skip

        raw_df = pd.read_csv(uploaded_file)
        raw_df.columns = [col.strip for col in raw_df.columns]
        uploaded_file.seek(0) #reset file pointer so load_transactions can read it again

        fingerprint = make_fingerprint(raw_df.columns)
        bank_name = detect_bank(raw_df.columns)
        fmt = None

        if bank_name:
            fmt = BANK_FORMATS[bank_name]
        elif fingerprint in bank_mappings:
            fmt = bank_mappings[fingerprint]
            bank_name = "Custom"

        if fmt is None:
            continue # unknown bank - handled by mapping UI in step 4

        df = load_transactions(uploaded_file, fmt)
        if df is not None:
            month_key, month_label = get_month_info(df)
            st.session_state.months[month_key]={
                "bank": bank_name,
                "month_label": month_label,
                "filename": uploaded_file.name,
                "outflow_df": df[df["Amount"] < 0].copy(),
                "inflow_df": apply_inflow_overrides(df[df["Amount"] > 0].copy()),
            }

    
    # -- Step 4: Mapping UI for unrecognised files -------------------
    processed_names= {v["filename"] for v in st.session.months.values()}

    for uploaded_file in uploaded_files:
        if uploaded_file.name in processed_names:
            continue
        uploaded_file.seek(0)
        raw_df = pd.read_csv(uploaded_file)
        raw_df.columns = [col.strip() for col in raw_df.columns]
        fingerprint = make_fingerprint(raw_df.columns)

        if detect_bank(raw_df.columns) is None and fingerprint not in bank_mappings:
            st.subheader(f"Map columns for '{uploaded_file.name}'")
            fmt = show_mapping_ui(raw_df, suffix = uploaded_file.name)
            if fmt is not None:
                bank_mappings[fingerprint] = fmt
                save_bank_mappings(bank_mappings)
                st.rerun() # forces a full rerun so the file is processed in step 3


    # ── Step 5: Build tabs ─────────────────────────────────────────────────────
    if not st.session_state.months:
        return

    sorted_months = sorted(st.session_state.months.items())
    # sorted() on "YYYY-MM" strings gives chronological order automatically

    for _, month in sorted_months:
        st.success(f"Detected: **{month['bank']}** — {month['month_label']} loaded")

    # Append Compare Months as the last tab
    all_tabs = st.tabs([m["month_label"] for _, m in sorted_months] + ["Compare Months"])

    # Render month tabs (all_tabs[:-1] excludes the last Compare tab)
    for tab, (month_key, _) in zip(all_tabs[:-1], sorted_months):
        with tab:
            render_month(month_key)

    # Render comparison tab (last element)
    with all_tabs[-1]:
        render_comparison()

main()