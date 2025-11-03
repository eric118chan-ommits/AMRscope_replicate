"""
AMR Mutation Database Access Tool
---------------------------------
Lightweight, dependency-minimal interface for querying the bundled
AMR-Collective mutations dataset stored as a Parquet file.

💾 Dataset location:
    data/mutations.parquet  (included in this repo)

The tool can be used both via command line (CLI) and directly in Python.

──────────────────────────────
Usage — Command Line Interface
──────────────────────────────

List available genes:
    python amr_db.py genes

List distinct organisms:
    python amr_db.py organisms

List distinct UniProt IDs:
    python amr_db.py uniprots

(Or use the generic version:)
    python amr_db.py values organism
    python amr_db.py values uniprot_id

─────────────────────
Query the dataset
─────────────────────
Filter rows by any combination of:
    --gene
    --organism
    --uniprot_id
    --limit (optional: restrict number of rows)

Examples:
    # By gene
    python amr_db.py query --gene pncA --limit 20

    # By organism
    python amr_db.py query --organism Enterococcus_faecium --limit 20

    # By UniProt ID
    python amr_db.py query --uniprot-id Q8P152 --limit 20

    # Combine filters
    python amr_db.py query --gene rpoB --organism Enterococcus_faecium --limit 20

──────────────────────────────
Usage — Within Python
──────────────────────────────

>>> from amr_db import (
...     query_mutations,
...     get_available_genes,
...     distinct_values,
... )

# List all genes
>>> get_available_genes()

# List all distinct organisms
>>> distinct_values("organism")

# Query mutations for a specific gene/organism
>>> df = query_mutations(gene="pncA", organism="MTB")
>>> df.head()

──────────────────────────────
Output
──────────────────────────────
All CLI queries print CSV-formatted output to stdout.
All Python queries return a pandas DataFrame.
"""

from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd
import typer

app = typer.Typer(no_args_is_help=True)

# ---------- Locate the Parquet file ----------
def _data_path() -> Path:
    """Try common locations for mutations.parquet."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "mutations.parquet",        
        here.parent / "mutations.parquet", 
        Path.cwd() / "mutations.parquet", 
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not find mutations.parquet.\n"
        "Tried:\n" + "\n".join(str(p) for p in candidates)
    )


ALLOWED_FILTERS = {
    "gene",
    "organism",
    "uniprot_id",
}

def _open_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE TABLE mutations AS SELECT * FROM parquet_scan('{_data_path()}');")
    return con

def get_available_genes() -> list[str]:
    con = _open_con()
    rows = con.execute("SELECT DISTINCT gene FROM mutations ORDER BY gene;").fetchall()
    return [r[0] for r in rows]

def distinct_values(column: str) -> list[str]:
    if column not in ALLOWED_FILTERS:
        raise ValueError(f"Column '{column}' not allowed. Choose from: {sorted(ALLOWED_FILTERS)}")
    con = _open_con()
    rows = con.execute(f"SELECT DISTINCT {column} FROM mutations WHERE {column} IS NOT NULL ORDER BY {column};").fetchall()
    return [r[0] for r in rows]

def query_mutations(
    gene: str | None = None,
    organism: str | None = None,
    uniprot_id: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Filter rows by any combination of gene, organism, uniprot_id.
    """
    con = _open_con()

    clauses = []
    params: list = []

    if gene is not None:
        clauses.append("gene = ?")
        params.append(gene)

    if organism is not None:
        clauses.append("organism = ?")
        params.append(organism)

    if uniprot_id is not None:
        clauses.append("uniprot_id = ?")
        params.append(uniprot_id)

    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    q = f"""
        SELECT *
        FROM mutations
        {where}
        ORDER BY gene, organism, position
    """
    if limit is not None:
        q += f" LIMIT {int(limit)}"

    return con.execute(q, params).df()

# ---------- CLI commands ----------
@app.command()
def genes():
    """List all genes in the dataset."""
    for g in get_available_genes():
        typer.echo(g)

# ---------- Convenience short commands ----------
@app.command("organisms")
def organisms():
    """List distinct organisms."""
    for v in distinct_values("organism"):
        typer.echo(v if v is not None else "")

@app.command("uniprots")
def uniprots():
    """List distinct UniProt IDs."""
    for v in distinct_values("uniprot_id"):
        typer.echo(v if v is not None else "")


@app.command()
def values(
    column: str = typer.Argument(..., help="One of: gene, organism, uniprot_id")
):
    """List distinct values for a column (useful for discovering valid filters)."""
    vals = distinct_values(column)
    for v in vals:
        typer.echo(v if v is not None else "")

@app.command()
def query(
    gene: str | None = typer.Option(None, help="Gene (e.g., pncA)"),
    organism: str | None = typer.Option(None, help="Organism code/name (exact match)"),
    uniprot_id: str | None = typer.Option(None, help="UniProt ID (e.g., P9WQG9)"),
    limit: int | None = typer.Option(None, help="Limit number of rows"),
):
    """Print filtered rows as CSV."""
    df = query_mutations(
        gene=gene,
        organism=organism,
        uniprot_id=uniprot_id,
        limit=limit,
    )
    if df.empty:
        typer.echo("No records found.")
    else:
        typer.echo(df.to_csv(index=False))

# ---------- Entry point ----------
if __name__ == "__main__":
    app()