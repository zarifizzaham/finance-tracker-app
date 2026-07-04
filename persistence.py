import json
import os
import streamlit as st

# ── Override dicts ──────────────────────────────────────────────────────────────
# Loaded once per Python process from disk; mutated in-place by the app.
# All modules import these references directly — mutations are visible everywhere.

def _load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

inflow_overrides  = _load_json("inflow_overrides.json")
outflow_overrides = _load_json("outflow_overrides.json")


# ── Transaction key ─────────────────────────────────────────────────────────────

def make_tx_key(row) -> str:
    return f"{row['Date']}|{row['Description']}|{row['Amount']}"

make_inflow_key = make_tx_key  # alias kept for backward compatibility


# ── Apply overrides to a freshly loaded DataFrame ───────────────────────────────

def apply_inflow_overrides(df):
    for idx, row in df.iterrows():
        key = make_tx_key(row)
        if key in inflow_overrides:
            df.at[idx, "Category"] = inflow_overrides[key]
    return df


def apply_outflow_overrides(df):
    for idx, row in df.iterrows():
        key = make_tx_key(row)
        if key in outflow_overrides:
            df.at[idx, "Category"] = outflow_overrides[key]
    return df


# ── Save helpers ────────────────────────────────────────────────────────────────

def save_categories():
    with open("categories.json", "w") as f:
        json.dump(st.session_state.categories, f)


def save_inflow_overrides():
    with open("inflow_overrides.json", "w") as f:
        json.dump(inflow_overrides, f)


def save_outflow_overrides():
    with open("outflow_overrides.json", "w") as f:
        json.dump(outflow_overrides, f)


# ── Bank mappings ───────────────────────────────────────────────────────────────

def load_bank_mappings() -> dict:
    return _load_json("bank_mappings.json")


def save_bank_mappings(mappings: dict):
    with open("bank_mappings.json", "w") as f:
        json.dump(mappings, f, indent=2)


# ── 50/30/20 bucket assignments ─────────────────────────────────────────────────

def load_bucket_assignments() -> dict:
    return _load_json("bucket_assignments.json")


def save_bucket_assignments(needs: list, wants: list):
    with open("bucket_assignments.json", "w") as f:
        json.dump({"needs": needs, "wants": wants}, f)
