from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._ledger import MultiLedgerLine, MultiLedgerLineImpl, read_all_dataframes


def withholding_tax(amount: NDArray[Any]) -> NDArray[Any]:
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        return np.where(
            amount > 1000000,
            round(1000000 * Decimal("0.1021") + (amount - 1000000) * Decimal("0.2042")),
            round(amount * Decimal("0.1021")),
        )


def ledger_from_sales(
    path: Path,
) -> Sequence[MultiLedgerLine[Any, Any]]:
    """
    Generate ledger from CSV files in the path.

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.

    Returns
    -------
    Sequence[MultiLedgerLine]
        The ledger lines.

    """
    df = read_all_dataframes(path / "sales")
    df["取引先"] = df["path"]
    df.fillna({"源泉徴収": 0, "手数料": 0}, inplace=True)

    ledger_lines: list[MultiLedgerLine[Any, Any]] = []
    for d, row in df.iterrows():
        ledger_lines.append(
            MultiLedgerLineImpl(
                date=d,
                debit=[("売掛金", row["金額"], row["通貨"])],
                credit=[("売上", row["金額"], row["通貨"])],
            )
        )
    for (_, d, c), df_ in df.groupby(["取引先", "振込日", "通貨"]):
        amount = df_["金額"].sum()
        if c == "":
            withholding = withholding_tax(
                df_.loc[df_["源泉徴収"] == True, "金額"].sum()
            )
            debit = [("事業主貸", amount - withholding, c)]
            if withholding > 0:
                debit.append(("仮払税金", withholding, c))
        else:
            if (df_["源泉徴収"] == True).any():
                raise ValueError("通貨が異なる取引に源泉徴収が含まれています。")
            debit = [("事業主貸", amount, c)]
        ledger_lines.append(
            MultiLedgerLineImpl(date=d, debit=debit, credit=[("売掛金", amount, c)])
        )
    if (df["発生日"] > df["振込日"]).any():
        raise ValueError("発生日が振込日より後の取引があります。")
    return ledger_lines
