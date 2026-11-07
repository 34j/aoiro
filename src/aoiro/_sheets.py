from collections.abc import Sequence
from itertools import groupby
from typing import Any

import networkx as nx

from ._ledger import Account, Currency, GeneralLedgerLine


def get_sheets(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
    G: nx.DiGraph,  # noqa: N803
    *,
    drop: bool = True,
) -> nx.DiGraph:
    """
    Get the blue return accounts as a graph.

    Returns
    -------
    nx.DiGraph
        Tree representation of the blue return account list.
        Has the following attributes:

        sum: dict[Currency, Decimal]
            The sum of the children for each currency,
            with alternating signs for each AccountType.

        sum_natural: dict[Currency, Decimal]
            The sum of the children for each currency.
            For accounts with AccountType well-defined, the sum is not
            altered.
            For accounts with AccountType None, the value is the same as sum.

    Raises
    ------
    ValueError
        If an account is not in the graph.

    """
    graph = G.copy()
    values = [value for line in lines for value in line.values]
    grouped = {
        k: list(v)
        for k, v in groupby(
            sorted(values, key=lambda x: (x.account, x.currency)),
            key=lambda x: (x.account, x.currency),
        )
    }
    grouped_nested = {k: dict(v) for k, v in groupby(grouped.items(), key=lambda x: x[0][0])}

    # Check that all accounts are in G
    all_accounts = set(grouped_nested.keys())
    all_accounts_graph = {d["label"] for n, d in graph.nodes(data=True) if not d["abstract"]}
    if all_accounts - all_accounts_graph:
        raise ValueError(f"{all_accounts - all_accounts_graph} not in G")

    # non-abstract accounts
    met_accounts: set[Any] = set()
    for n in reversed(list(nx.topological_sort(graph))):
        d = graph.nodes[n]
        successors = list(graph.successors(n))
        add_current = (not d["abstract"]) and d["label"] in (all_accounts - met_accounts)
        if successors or add_current:
            graph.nodes[n]["sum"] = _dict_sum(
                [graph.nodes[child]["sum"] for child in successors]
                + (
                    [
                        {
                            currency: sum(el.amount for el in values)
                            * (1 if d["account_type"].debit else -1)
                            for (_, currency), values in grouped_nested[d["label"]].items()
                        }
                    ]
                    if add_current
                    else []
                )
            )
            if add_current:
                met_accounts.add(d["label"])
        elif drop:
            graph.remove_node(n)
        else:
            graph.nodes[n]["sum"] = {}

    # natural sum
    for n, d in graph.nodes(data=True):
        account_type = d["account_type"]
        if account_type is not None:
            graph.nodes[n]["sum_natural"] = {
                k: v * (1 if account_type.debit else -1) for k, v in d["sum"].items()
            }
        else:
            graph.nodes[n]["sum_natural"] = d["sum"]
    return graph


def _dict_sum(
    ds: Sequence[dict[Any, Any]],
    /,
) -> dict[Any, Any]:
    """
    Sum dictionaries.

    Return a dictionary which,
    for any key in any of the dictionaries,
    contains the sum of the values of that key in all dictionaries
    where the key is present.

    Parameters
    ----------
    ds : Sequence[dict[Any, Any]]
        The dictionaries to sum.

    Returns
    -------
    dict[Any, Any]
        The sum of the dictionaries.

    """
    return {k: sum(d.get(k, 0) for d in ds) for k in set().union(*ds)}
