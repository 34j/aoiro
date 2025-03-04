from datetime import datetime
from pathlib import Path

# from rich import print
import attrs
import networkx as nx
import pandas as pd
import typer
from account_codes_jp import get_account_type_factory, get_blue_return_accounts
from networkx.readwrite.text import generate_network_text
from rich import print

from ._expenses import ledger_from_expenses
from ._ledger import (
    generalledger_to_multiledger,
    multiledger_to_ledger,
)
from ._multidimensional import multidimensional_ledger_to_ledger
from ._sales import ledger_from_sales
from ._sheets import get_sheets

app = typer.Typer(pretty_exceptions_enable=True)


@app.command()
def _main(path: Path, year: int | None = None, drop: bool = True) -> None:
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
    f = get_account_type_factory(G)

    def is_debit(x: str) -> bool:
        v = getattr(f(x), "debit", None)
        if v is None:
            raise ValueError(f"Account {x} not recognized")
        return v

    gledger_vec = list(ledger_from_sales(path)) + list(ledger_from_expenses(path))
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
    for n, d in G.nodes(data=True):
        G.nodes[n]["label"] = f"{d['label']}/{d['sum'].get('', 0)}"
    for line in generate_network_text(G, with_labels=True):
        print(line)
