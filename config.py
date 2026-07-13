BANK_FORMATS = {
    "Revolut": {
        "date_col":        "Started Date",
        "date_format":     "%d/%m/%Y %H:%M",
        "description_col": "Description",
        "amount_col":      "Amount",
    },
    "Monzo": {
        "date_col":        "Date",
        "date_format":     "%d/%m/%Y",
        "description_col": "Name",
        "amount_col":      "Amount",
    },
    "Barclays": {
        "date_col":        "Date",
        "date_format":     "%d/%m/%Y",
        "description_col": "Memo",
        "amount_col":      "Amount",
    },
    "Starling": {
        "date_col":        "Date",
        "date_format":     "%d/%m/%Y",
        "description_col": "Counter Party",
        "amount_col":      "Amount (GBP)",
    },
    "HSBC": {
        "date_col":        "Date",
        "date_format":     "%d/%m/%Y",
        "description_col": "Payee",
        "debit_col":       "Paid out",
        "credit_col":      "Paid in",
    },
    "Lloyds": {
        "date_col":        "Transaction Date",
        "date_format":     "%d/%m/%Y",
        "description_col": "Transaction Description",
        "debit_col":       "Debit Amount",
        "credit_col":      "Credit Amount",
    },
}

DATE_FORMAT_OPTIONS = {
    "dd/mm/YYYY HH:MM  (e.g. 01/06/2026 14:30)": "%d/%m/%Y %H:%M",
    "dd/mm/YYYY        (e.g. 01/06/2026)":        "%d/%m/%Y",
    "YYYY-MM-DD        (e.g. 2026-06-01)":        "%Y-%m-%d",
    "mm/dd/YYYY        (e.g. 06/01/2026)":        "%m/%d/%Y",
    "dd-mm-YYYY        (e.g. 01-06-2026)":        "%d-%m-%Y",
    "dd MMM YYYY       (e.g. 01 Jun 2026)":       "%d %b %Y",
    "YYYY/mm/dd        (e.g. 2026/06/01)":        "%Y/%m/%d",
}
