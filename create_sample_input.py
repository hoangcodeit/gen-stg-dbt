"""Run once to create sample input files for testing."""
import pandas as pd
from pathlib import Path

Path("input").mkdir(exist_ok=True)

# FILE 1: tables.csv - actual source table structure
tables_data = [
    ("dna_oaisbank_acct",  "acct_id"),
    ("dna_oaisbank_acct",  "acct_no"),
    ("dna_oaisbank_acct",  "cust_id"),
    ("dna_oaisbank_acct",  "open_dt"),
    ("dna_oaisbank_acct",  "bal_amt"),
    ("dna_oaisbank_loan",  "loan_id"),
    ("dna_oaisbank_loan",  "acct_id"),
    ("dna_oaisbank_loan",  "prin_amt"),
    ("dna_oaisbank_loan",  "int_rate"),
    ("dna_oaisbank_loan",  "due_dt"),
]
df_tables = pd.DataFrame(tables_data, columns=["table_name", "column_name"])
df_tables.to_csv("input/tables.csv", index=False, encoding="utf-8-sig")
print("Created input/tables.csv")
print(df_tables.to_string(index=False))

print()

# FILE 2: metadata.csv - data dictionary
meta_data = [
    ("acct", "Bang tai khoan",  "acct_id",   "Ma tai khoan"),
    ("acct", "Bang tai khoan",  "acct_no",   "So tai khoan"),
    ("acct", "Bang tai khoan",  "cust_id",   "Ma khach hang"),
    ("acct", "Bang tai khoan",  "open_dt",   "Ngay mo tai khoan"),
    ("acct", "Bang tai khoan",  "bal_amt",   "So du tai khoan"),
    ("loan", "Bang khoan vay",  "loan_id",   "Ma khoan vay"),
    ("loan", "Bang khoan vay",  "acct_id",   "Ma tai khoan lien ket"),
    ("loan", "Bang khoan vay",  "prin_amt",  "So tien goc"),
    ("loan", "Bang khoan vay",  "int_rate",  "Lai suat"),
    ("loan", "Bang khoan vay",  "due_dt",    "Ngay den han"),
]
df_meta = pd.DataFrame(meta_data, columns=[
    "ten_bang", "mo_ta_ten_bang", "ten_truong", "mo_ta_truong_du_lieu"
])
df_meta.to_csv("input/metadata.csv", index=False, encoding="utf-8-sig")
print("Created input/metadata.csv")
print(df_meta.to_string(index=False))
