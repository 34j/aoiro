from collections.abc import Sequence
from itertools import groupby
from typing import Any

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
    grouped = {
        k: list(v)
        for k, v in groupby(
            sorted(values, key=lambda x: (x[0], x[2])), key=lambda x: (x[0], x[2])
        )
    }
    grouped_nested = {
        k: dict(v) for k, v in groupby(grouped.items(), key=lambda x: x[0][0])
    }

    # Check that all accounts are in G
    all_accounts = set(grouped_nested.keys())
    all_accounts_G = {d["label"] for n, d in G.nodes(data=True) if not d["abstract"]}
    if all_accounts - all_accounts_G:
        raise ValueError(f"{all_accounts - all_accounts_G} not in G")

    # non-abstract accounts
    for n, d in G.copy().nodes(data=True):
        if d["abstract"]:
            continue
        if d["label"] not in all_accounts:
            if drop:
                G.remove_node(n)
            else:
                G.nodes[n]["sum"] = {}
            continue
        sum_ = {
            currency: sum(v for _, v, _ in values)
            for (_, currency), values in grouped_nested[d["label"]].items()
        }
        G.nodes[n]["sum"] = sum_

    # sum up children
    for n in reversed(list(nx.topological_sort(G))):
        if not G.nodes[n]["abstract"]:
            continue
        successors = list(G.successors(n))
        if successors:
            G.nodes[n]["sum"] = _dict_sum(
                [G.nodes[child]["sum"] for child in successors]
            )
        else:
            if drop:
                G.remove_node(n)
            else:
                G.nodes[n]["sum"] = {}
    return G


def _dict_sum(
    ds: Sequence[dict[Any, Any]],
    /,
) -> dict[Any, Any]:
    return {k: sum([d.get(k, 0) for d in ds]) for k in set().union(*ds)}
