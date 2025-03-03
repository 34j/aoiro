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
def _main(path: Path) -> None:
    def patch_G(G: nx.DiGraph) -> nx.DiGraph:
        G.add_node(-2, label="為替差損益")
        G.add_edge(next(n for n, d in G.nodes(data=True) if d["label"] == "売上"), -2)
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
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(
            pd.DataFrame([attrs.asdict(line) for line in ledger])  # type: ignore
            .set_index("date")
            .sort_index(axis=0)
        )
    G = get_sheets(gledger, G, drop=True)
    print(nx.get_node_attributes(G, "sum"))
    for n, d in G.nodes(data=True):
        G.nodes[n]["label"] = f"{d['label']}/{d['sum'].get('', 0)}"
    for line in generate_network_text(G, with_labels=True):
        print(line)
