from datetime import datetime
from pathlib import Path

# from rich import print
import attrs
import cyclopts
import networkx as nx
import pandas as pd
from account_codes_jp import (
    get_account_type_factory,
    get_blue_return_accounts,
    get_node_from_label,
)
from networkx.readwrite.text import generate_network_text
from rich import print

from ._ledger import (
    generalledger_to_multiledger,
    multiledger_to_ledger,
)
from ._multidimensional import multidimensional_ledger_to_ledger
from ._sheets import get_sheets
from .reader._expenses import ledger_from_expenses
from .reader._io import read_general_ledger
from .reader._sales import ledger_from_sales

app = cyclopts.App(name="aoiro")


@app.default
def metrics(path: Path, year: int | None = None, drop: bool = True) -> None:
    """
    Calculate metrics needed for tax declaration.

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.
    year : int | None, optional
        The year to calculate, by default None.
        If None, the previous year would be used.
    drop : bool, optional
        Whether to drop unused accounts, by default True.

    """
    if year is None:
        year = datetime.now().year - 1

    def patch_G(G: nx.DiGraph) -> nx.DiGraph:
        G.add_node(-1, label="為替差益")
        G.add_node(-2, label="為替差損")
        G.add_edge(next(n for n, d in G.nodes(data=True) if d["label"] == "売上"), -1)
        G.add_edge(
            next(n for n, d in G.nodes(data=True) if d["label"] == "経費追加"), -2
        )
        return G

    G = get_blue_return_accounts(patch_G)

    gledger_vec = (
        list(ledger_from_sales(path, G))
        + list(ledger_from_expenses(path))
        + list(read_general_ledger(path))
    )
    f = get_account_type_factory(G)

    def is_debit(x: str) -> bool:
        v = getattr(f(x), "debit", None)
        if v is None:
            raise ValueError(f"Account {x} not recognized")
        return v

    gledger = multidimensional_ledger_to_ledger(gledger_vec, is_debit=is_debit)
    ledger = multiledger_to_ledger(
        generalledger_to_multiledger(gledger, is_debit=is_debit)
    )
    ledger_now = [line for line in ledger if line.date.year == year]
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(
            pd.DataFrame([attrs.asdict(line) for line in ledger_now])  # type: ignore
            .set_index("date")
            .sort_index(axis=0)
        )
    gledger_now = [line for line in gledger if line.date.year == year]
    G = get_sheets(gledger_now, G, drop=drop)
    G_print = G.copy()
    for n, d in G_print.nodes(data=True):
        G_print.nodes[n]["label"] = f"{d['label']}/{d['sum_natural'].get('', 0)}"
    for line in generate_network_text(G_print, with_labels=True):
        print(line)

    # sales per month
    print("Sales per month")
    for month in range(1, 13):
        G_month = get_sheets(
            [line for line in gledger_now if line.date.month == month], G, drop=False
        )
        sales_deeper_node = get_node_from_label(
            G, "売上", lambda x: not G.nodes[x]["abstract"]
        )
        sales_deeper = G_month.nodes[sales_deeper_node]["sum_natural"].get("", 0)
        print(f"{month}: {sales_deeper}")
