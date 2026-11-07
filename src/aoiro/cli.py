from datetime import UTC, datetime
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
from rich import print  # noqa: A004

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
def metrics(  # noqa: C901
    path: Path,
    years: str | None = None,
    months: str | None = None,
    drop: bool = True,  # noqa: FBT001, FBT002
) -> int:
    """
    Calculate metrics needed for tax declaration.

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.
    years : str | None, optional
        The year to calculate, by default None.
        If None, the previous year would be used.
    months : str | None, optional
        The months to calculate, by default None.
    drop : bool, optional
        Whether to drop unused accounts, by default True.

    Returns
    -------
    int
        Zero on success, or one if no ledger lines were found.

    """
    if years == "all":
        years_ = None
    elif years is None:
        years_ = [datetime.now(UTC).year - 1]
    else:
        years_ = sorted({int(y) for y in years.split(",")})
    months_ = list(range(1, 13))
    if months is not None:
        months_ = sorted({int(m) for m in months.split(",")})

    def patch_graph(graph: nx.DiGraph) -> nx.DiGraph:
        graph.add_node(-1, label="為替差益")
        graph.add_node(-2, label="為替差損")
        graph.add_edge(next(n for n, d in graph.nodes(data=True) if d["label"] == "売上"), -1)
        graph.add_edge(next(n for n, d in graph.nodes(data=True) if d["label"] == "経費追加"), -2)
        return graph

    graph = get_blue_return_accounts(patch_graph)
    gledger_vec = (
        list(ledger_from_sales(path, graph))
        + list(ledger_from_expenses(path))
        + list(read_general_ledger(path))
    )
    gledger_vec = sorted(gledger_vec, key=lambda x: x.date)
    f = get_account_type_factory(graph)

    def is_debit(x: str) -> bool:
        v = getattr(f(x), "debit", None)
        if v is None:
            raise ValueError(f"Account {x} not recognized")
        return v

    gledger = multidimensional_ledger_to_ledger(gledger_vec, is_debit=is_debit)
    multiledger = generalledger_to_multiledger(gledger, is_debit=is_debit)
    ledger = multiledger_to_ledger(multiledger)
    ledger_now = [
        line
        for line in ledger
        if (years_ is None or line.date.year in years_) and line.date.month in months_
    ]
    if len(ledger_now) == 0:
        print(f"No ledger lines found for year {years}")
        return 1
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(
            pd
            .DataFrame([attrs.asdict(line) for line in ledger_now])  # type: ignore[arg-type]
            .set_index("date")
            .sort_index(axis=0)
        )
    gledger_now = [
        line
        for line in gledger
        if (line.date.year in years_ if years_ is not None else True) and line.date.month in months_
    ]
    graph = get_sheets(gledger_now, graph, drop=drop)
    graph_print = graph.copy()
    for n, d in graph_print.nodes(data=True):
        graph_print.nodes[n]["label"] = f"{d['label']}/{d['sum_natural'].get('', 0)}"
    for line in generate_network_text(graph_print, with_labels=True):
        print(line)

    # sales per month
    print("Sales per month")
    for year in years_ if years_ is not None else [datetime.now(UTC).year - 1]:
        for month in months_:
            graph_month = get_sheets(
                [
                    line
                    for line in gledger_now
                    if (line.date.year == year if year is not None else True)
                    and line.date.month == month
                ],
                graph,
                drop=False,
            )
            sales_deeper_node = get_node_from_label(
                graph, "売上", lambda x: not graph.nodes[x]["abstract"]
            )
            sales_deeper = graph_month.nodes[sales_deeper_node]["sum_natural"].get("", 0)
            print(f"{month}: {sales_deeper}")
    return 0
