from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd
from account_codes_jp import get_node_from_label

from .._ledger import GeneralLedgerLineImpl, LedgerElementImpl
from ._io import read_simple_csvs


def withholding_tax(amount: Decimal) -> Decimal:
    """
    Withholding tax calculation for most 源泉徴収が必要な報酬・料金等.

    Parameters
    ----------
    amount : Decimal
        The raw amount.

    Returns
    -------
    Decimal
        The withholding tax amount.

    References
    ----------
    https://www.nta.go.jp/taxes/shiraberu/taxanswer/gensen/2792.htm

    """
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        if amount > 1000000:
            return round(
                Decimal(
                    1000000 * Decimal("0.1021") + (amount - 1000000) * Decimal("0.2042")
                ),
                0,
            )
        else:
            return round(amount * Decimal("0.1021"), 0)


def ledger_from_sales(
    path: Path,
    G: nx.DiGraph | None = None,
) -> Sequence[GeneralLedgerLineImpl[Any, Any]]:
    """
    Generate ledger from sales.

    The CSV files are assumed to have columns
    ["発生日", "金額", "振込日", "源泉徴収", "手数料"].
    If "源泉徴収" is True, the amount would be assumed by `withholding_tax()`.
    If "源泉徴収" if False or NaN, the amount would be assumed as 0.
    If "源泉徴収" is numeric, the amount would be assumed as 源泉徴収額.
    The relative path of the CSV file would be used as "取引先".

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.
    G : nx.DiGraph | None
        The graph of accounts, by default None.
        If provided, each "取引先" would be added as a child node of "売上".

    Returns
    -------
    Sequence[GneralLedgerLineImpl[Any, Any]]
        The ledger lines.

    Raises
    ------
    ValueError
        If the transaction date is later than the transfer date.
    ValueError
        If withholding tax is included in transactions with different currencies.

    """
    df = read_simple_csvs(path / "sales")
    if df.empty:
        return []
    df["取引先"] = df["path"].str.replace(".csv", "")
    df["手数料"] = df["手数料"].apply(
        lambda x: Decimal(x) if pd.notna(x) else Decimal(0)
    )
    df["源泉徴収"] = df["源泉徴収"].replace(
        {"True": True, "False": False, "true": True, "false": False}
    )
    df.fillna({"源泉徴収": Decimal(0)}, inplace=True)

    if G is not None:
        for ca in ["売上", "仮払税金"]:
            parent_node = get_node_from_label(
                G, ca, lambda x: not G.nodes[x]["abstract"]
            )
            parent_node_attrs = G.nodes[parent_node]
            for t in df["取引先"].unique():
                t_attrs = {**parent_node_attrs, "label": f"{ca}({t})"}
                t_id = f"{ca}({t})"
                G.add_node(t_id, **t_attrs)
                G.add_edge(parent_node, t_id)

    ledger_lines: list[GeneralLedgerLineImpl[Any, Any]] = []
    for date, row in df.iterrows():
        ledger_lines.append(
            GeneralLedgerLineImpl(
                date=date,
                values=[
                    LedgerElementImpl(
                        account="売掛金", amount=row["金額"], currency=row["通貨"]
                    ),
                    LedgerElementImpl(
                        account="売上" if G is None else f"売上({row['取引先']})",
                        amount=row["金額"],
                        currency=row["通貨"],
                    ),
                ],
            )
        )
    for (t, date, currency), df_ in df.groupby(["取引先", "振込日", "通貨"]):
        fees = Decimal(df_["手数料"].sum())
        receivable = Decimal(df_["金額"].sum())
        recievable_without_fees = receivable - fees
        if currency == "":
            withholding = withholding_tax(
                df_.loc[df_["源泉徴収"] == True, "金額"].sum()
            )
            values = [
                LedgerElementImpl(
                    account="事業主貸",
                    amount=recievable_without_fees - withholding,
                    currency=currency,
                )
            ]
            if withholding > 0:
                values.append(
                    LedgerElementImpl(
                        account=f"仮払税金({t})", amount=withholding, currency=currency
                    )
                )
        else:
            if (df_["源泉徴収"] == True).any():
                raise ValueError("通貨が異なる取引に源泉徴収が含まれています。")
            values = [
                LedgerElementImpl(
                    account="事業主貸",
                    amount=recievable_without_fees,
                    currency=currency,
                )
            ]
        if fees > 0:
            values.append(
                LedgerElementImpl(account="支払手数料", amount=fees, currency=currency)
            )
        ledger_lines.append(
            GeneralLedgerLineImpl(
                date=date,
                values=[
                    *values,
                    LedgerElementImpl(
                        account="売掛金", amount=-receivable, currency=currency
                    ),
                ],
            )
        )
    if (df["発生日"] > df["振込日"]).any():
        raise ValueError("発生日が振込日より後の取引があります。")
    return ledger_lines
