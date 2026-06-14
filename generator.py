"""
dbt Staging Layer Generator

Input files:
  tables.csv   - columns: table_name, column_name
                 e.g.  dna_oaisbank_acct | acct_id
  metadata.csv - columns: ten_bang, mo_ta_ten_bang, ten_truong, mo_ta_truong_du_lieu
                 e.g.  acct | Bang tai khoan | acct_id | Ma tai khoan

Mapping: dna_oaisbank_acct -> table_short=acct -> match ten_bang=acct in metadata
"""

import sys
import yaml
import pandas as pd
from pathlib import Path


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_file(path: Path, cfg: dict) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        encoding = cfg.get("csv_encoding", "utf-8-sig")
        sep = cfg.get("csv_separator", ",")
        df = pd.read_csv(path, dtype=str, encoding=encoding, sep=sep)
    elif ext in (".xlsx", ".xls"):
        sheet = cfg.get("metadata_sheet", 0)
        df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    else:
        print(f"[ERROR] Unsupported file type '{ext}'. Use .csv, .xlsx, or .xls")
        sys.exit(1)
    df.columns = df.columns.str.strip()
    return df.fillna("").map(str.strip)


def load_tables(cfg: dict) -> pd.DataFrame:
    """
    Load tables.csv -> returns DataFrame with columns: table_name, column_name
    e.g.:
      table_name           | column_name
      dna_oaisbank_acct    | acct_id
      dna_oaisbank_acct    | acct_no
    """
    path = Path(cfg["tables_file"])
    cols_cfg = cfg["tables_columns"]
    df = _read_file(path, cfg)

    col_table = cols_cfg["table_name"]
    col_column = cols_cfg["column_name"]
    missing = [c for c in [col_table, col_column] if c not in df.columns]
    if missing:
        print(f"[ERROR] Missing columns in '{path.name}': {missing}")
        print(f"        Found: {list(df.columns)}")
        sys.exit(1)

    df = df[[col_table, col_column]].copy()
    df.columns = ["table_name", "column_name"]
    df = df.dropna(subset=["table_name", "column_name"])
    df["table_name"] = df["table_name"].str.lower().str.strip()
    df["column_name"] = df["column_name"].str.lower().str.strip()
    df = df[df["table_name"] != ""]
    df = df[df["column_name"] != ""]
    return df


def load_metadata(cfg: dict) -> pd.DataFrame:
    """
    Load metadata.csv -> returns DataFrame with columns:
      table_short, table_desc, column_name, column_desc
    """
    path = Path(cfg["metadata_file"])
    cols = cfg["metadata_columns"]
    df = _read_file(path, cfg)

    required = [cols["table_short_name"], cols["table_description"],
                cols["column_name"], cols["column_description"]]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[ERROR] Missing columns in '{path.name}': {missing}")
        print(f"        Found: {list(df.columns)}")
        sys.exit(1)

    df = df[required].copy()
    df.columns = ["table_short", "table_desc", "column_name", "column_desc"]
    df = df.dropna(subset=["table_short", "column_name"])
    df = df[df["table_short"] != ""]
    return df


def parse_table_name(full_name: str):
    """
    dna_oaisbank_acct -> (prefix='dna', domain='oaisbank', table_short='acct')
    """
    parts = full_name.split("_", 2)
    if len(parts) < 3:
        print(f"[WARN] Cannot parse '{full_name}', expected {{prefix}}_{{domain}}_{{table}}")
        return None, None, None
    return parts[0], parts[1], parts[2]


def build_tables(tables_df: pd.DataFrame, metadata_df: pd.DataFrame) -> list[dict]:
    """
    For each unique table_name in tables_df:
      - parse domain + table_short
      - get ordered columns from tables_df
      - join with metadata_df on (table_short, column_name) to get descriptions
    """
    # metadata index: {table_short: {column_name: {table_desc, column_desc}}}
    meta_index = {}
    for _, row in metadata_df.iterrows():
        ts = row["table_short"]
        if ts not in meta_index:
            meta_index[ts] = {"_table_desc": row["table_desc"], "columns": {}}
        meta_index[ts]["columns"][row["column_name"]] = row["column_desc"]

    tables = []
    for full_name, group in tables_df.groupby("table_name", sort=False):
        prefix, domain, table_short = parse_table_name(full_name)
        if table_short is None:
            continue

        meta = meta_index.get(table_short)
        if meta is None:
            print(f"[WARN] No metadata entry for table_short='{table_short}' ('{full_name}')")

        table_desc = meta["_table_desc"] if meta else ""
        columns = []
        for _, row in group.iterrows():
            col_name = row["column_name"]
            col_desc = meta["columns"].get(col_name, "") if meta else ""
            if not col_desc:
                print(f"[WARN] No description for column '{col_name}' in '{table_short}'")
            columns.append({"name": col_name, "desc": col_desc})

        tables.append({
            "full_name": full_name,
            "prefix": prefix,
            "domain": domain,
            "table_short": table_short,
            "desc": table_desc,
            "columns": columns,
        })

    return tables


# ── Generators ────────────────────────────────────────────────────────────────

def generate_source_yml(cfg: dict, tables: list[dict]) -> str:
    src = cfg["source"]
    lines = [
        "version: 2",
        "",
        "sources:",
        f'  - name: {src["name"]}',
        f'    database: {src["database"]}',
        f'    schema: {src["schema"]}',
        "    tables:",
    ]
    for t in tables:
        lines.append(f'      - name: {t["full_name"]}')
        if t["desc"]:
            lines.append(f'        description: "{t["desc"]}"')
        if t["columns"]:
            lines.append("        columns:")
            for col in t["columns"]:
                lines.append(f'          - name: {col["name"]}')
                if col["desc"]:
                    lines.append(f'            description: "{col["desc"]}"')
    lines.append("")
    return "\n".join(lines)


def generate_models_yml(tables: list[dict]) -> str:
    lines = ["version: 2", "", "models:"]
    for t in tables:
        model_name = f'stg_{t["domain"]}_{t["table_short"]}'
        lines.append(f'  - name: {model_name}')
        if t["desc"]:
            lines.append(f'    description: "{t["desc"]}"')
        if t["columns"]:
            lines.append("    columns:")
            for col in t["columns"]:
                lines.append(f'      - name: {col["name"]}')
                if col["desc"]:
                    lines.append(f'        description: "{col["desc"]}"')
    lines.append("")
    return "\n".join(lines)


def generate_staging_sql(cfg: dict, t: dict) -> str:
    src_name = cfg["source"]["name"]
    col_list = ",\n        ".join(col["name"] for col in t["columns"]) if t["columns"] else "*"
    return (
        f"with source as (\n"
        f"    select * from {{{{ source('{src_name}', '{t['full_name']}') }}}}\n"
        f"),\n\n"
        f"final as (\n"
        f"    select\n"
        f"        {col_list}\n"
        f"    from source\n"
        f")\n\n"
        f"select * from final\n"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()

    tables_df = load_tables(cfg)
    metadata_df = load_metadata(cfg)
    tables = build_tables(tables_df, metadata_df)

    if not tables:
        print("[ERROR] No valid tables found. Check your input files.")
        sys.exit(1)

    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    source_yml_path = out_dir / "_dna_source.yml"
    source_yml_path.write_text(generate_source_yml(cfg, tables), encoding="utf-8")
    print(f"[OK] {source_yml_path}")

    models_yml_path = out_dir / "_dna_models.yml"
    models_yml_path.write_text(generate_models_yml(tables), encoding="utf-8")
    print(f"[OK] {models_yml_path}")

    for t in tables:
        sql_path = out_dir / f'stg_{t["domain"]}_{t["full_name"]}.sql'
        sql_path.write_text(generate_staging_sql(cfg, t), encoding="utf-8")
        print(f"[OK] {sql_path}")

    print(f"\nDone. {len(tables)} table(s) processed -> {out_dir}/")


if __name__ == "__main__":
    main()
