import streamlit as st
import pandas as pd
from config import BANK_FORMATS
from categories import categorize_transactions


def make_fingerprint(columns) -> str:
    return ",".join(sorted(c.strip() for c in columns))


def detect_bank(columns) -> str | None:
    col_set = set(columns)
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
    return None


def normalise_df(df, fmt: dict) -> pd.DataFrame:
    df = df.copy()
    try:
        df["Date"] = pd.to_datetime(df[fmt["date_col"]], format=fmt["date_format"]).dt.date
    except ValueError:
        df["Date"] = pd.to_datetime(df[fmt["date_col"]], format="mixed", dayfirst=True).dt.date
    df["Description"] = df[fmt["description_col"]].astype(str).str.strip()
    if "debit_col" in fmt and "credit_col" in fmt:
        debit  = pd.to_numeric(df[fmt["debit_col"]].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        credit = pd.to_numeric(df[fmt["credit_col"]].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["Amount"] = credit - debit
    else:
        df["Amount"] = pd.to_numeric(df[fmt["amount_col"]].astype(str).str.replace(",", ""), errors="coerce")
    return df[["Date", "Description", "Amount"]].dropna(subset=["Amount"])


def load_transactions(file, fmt: dict) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]
        df = normalise_df(df, fmt)
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None


def get_month_info(df) -> tuple[str, str]:
    # Use the dominant month so a CSV starting on Apr 30 but mostly May is labelled May.
    dominant = pd.to_datetime(df["Date"]).dt.to_period("M").value_counts().idxmax()
    dt = dominant.to_timestamp()
    return dt.strftime("%Y-%m"), dt.strftime("%B %Y")
