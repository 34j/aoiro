from collections.abc import Sequence
from itertools import groupby

import networkx as nx

from ._ledger import Account, Currency, GeneralLedgerLine


def get_sheets(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
    G: nx.DiGraph,
    *,
    drop: bool = True,
) -> nx.DiGraph:
    """
    Get the blue return accounts as a graph.

    Returns
    -------
    nx.DiGraph
        Tree representation of the blue return account list
        sum: dict[Account, Decimal]

    """
    values = [value for line in lines for value in line.values]
    print(values)
    grouped = {
        k: list(v)
        for k, v in groupby(
            sorted(values, key=lambda x: (x[0], x[2])), key=lambda x: (x[0], x[2])
        )
    }
    grouped_nested = {
        k: dict(v) for k, v in groupby(grouped.items(), key=lambda x: x[0][0])
    }
    print(grouped_nested, grouped)

    # Check that all accounts are in G
    all_accounts = set(grouped_nested.keys())
    all_accounts_G = {d["label"] for n, d in G.nodes(data=True) if not d["abstract"]}
    if all_accounts - all_accounts_G:
        raise ValueError(f"{all_accounts - all_accounts_G} not in G")

    G_new = G.copy()
    for n, d in G.nodes(data=True):
        if d["abstract"]:
            continue
        if d["label"] not in all_accounts:
            if drop:
                G_new.remove_node(n)
            else:
                G_new.nodes[n]["sum"] = {}
            continue
        print(d["label"])
        print(grouped_nested[d["label"]])
        sum_ = {
            currency: sum(v for _, v, _ in values)
            for (_, currency), values in grouped_nested[d["label"]].items()
        }
        print(sum_)
        G_new.nodes[n]["sum"] = sum_
    for n in reversed(list(nx.topological_sort(G_new))):
        G_new.nodes[n]["sum"] = sum(
            G_new.nodes[child]["sum"] for child in G_new.successors(n)
        )
    return G_new
