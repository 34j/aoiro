from datetime import datetime
from pathlib import Path
from typing import Any

# from rich import print
import attrs
import networkx as nx
import pandas as pd
import typer
from account_codes_jp import (
    get_account_type_factory,
    get_blue_return_accounts,
    get_node_from_label,
)
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

    gledger_vec = list(ledger_from_sales(path, G)) + list(ledger_from_expenses(path))
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
    G = get_sheets(gledger_now, G, drop=False)
    G_print = G.copy()
    for n, d in G_print.nodes(data=True):
        G_print.nodes[n]["label"] = f"{d['label']}/{d['sum'].get('', 0)}"
    for line in generate_network_text(G_print, with_labels=True):
        print(line)

    # start of p.1
    print("p.1")
    print("損益計画書（自1月1日至12月31日）")
    vals: list[Any] = [0]
    vals.extend(
        [
            -G.nodes[get_node_from_label(G, "売上")]["sum"].get("", 0),
            G.nodes[get_node_from_label(G, "期首商品棚卸高")]["sum"].get("", 0),
            G.nodes[get_node_from_label(G, "仕入")]["sum"].get("", 0),
        ]
    )
    vals.append(vals[2] + vals[3])
    vals.append(G.nodes[get_node_from_label(G, "期末商品棚卸高")]["sum"].get("", 0))
    vals.append(vals[4] - vals[5])
    vals.append(vals[1] - vals[6])
    for v in list(G.successors(get_node_from_label(G, "経費")))[:-1]:
        vals.append(G.nodes[v]["sum"].get("", 0))
    for v in G.successors(get_node_from_label(G, "経費追加")):
        val = G.nodes[v]["sum"].get("", 0)
        if val == 0:
            continue
        vals.append((G.nodes[v]["label"], val))
    for _ in range(31 - len(vals)):
        vals.append(0)
    vals.append(
        G.nodes[list(G.successors(get_node_from_label(G, "経費")))[-1]]["sum"].get(
            "", 0
        )
    )
    vals.append(G.nodes[get_node_from_label(G, "経費")]["sum"].get("", 0))
    vals.append(vals[7] - vals[32])
    for v in G.successors(
        get_node_from_label(
            G,
            "各種引当金・準備金等",
            lambda x: get_node_from_label(G, "収益") in G.predecessors(x),
        )
    ):
        vals.append(G.nodes[v]["sum"].get("", 0))
    for _ in range(37 - len(vals)):
        vals.append(0)
    vals.append(
        G.nodes[
            get_node_from_label(
                G,
                "各種引当金・準備金等",
                lambda x: get_node_from_label(G, "収益") in G.predecessors(x),
            )
        ]["sum"].get("", 0)
    )
    for v in G.successors(
        get_node_from_label(
            G,
            "各種引当金・準備金等",
            lambda x: get_node_from_label(G, "費用") in G.predecessors(x),
        )
    ):
        vals.append(G.nodes[v]["sum"].get("", 0))
    for _ in range(42 - len(vals)):
        vals.append(0)
    vals.append(
        G.nodes[
            get_node_from_label(
                G,
                "各種引当金・準備金等",
                lambda x: get_node_from_label(G, "費用") in G.predecessors(x),
            )
        ]["sum"].get("", 0)
    )
    vals.append(vals[33] + vals[37] - vals[42])
    vals.append(min(vals[43], 650000))
    vals.append(vals[43] - vals[44])
    for i, v in enumerate(vals):
        if i == 0:
            continue
        print(f"{i}: {v}")
