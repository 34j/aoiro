from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._io import read_all_dataframes
from ._ledger import GeneralLedgerLineImpl, LedgerElementImpl


def withholding_tax(amount: NDArray[Any]) -> NDArray[Any]:
    """
    Withholding tax calculation for most 源泉徴収が必要な報酬・料金等.

    Parameters
    ----------
    amount : NDArray[Any]
        The raw amount.

    Returns
    -------
    NDArray[Any]
        The withholding tax amount.

    References
    ----------
    https://www.nta.go.jp/taxes/shiraberu/taxanswer/gensen/2792.htm

    """
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        return np.where(
            amount > 1000000,
            round(1000000 * Decimal("0.1021") + (amount - 1000000) * Decimal("0.2042")),
            round(amount * Decimal("0.1021")),
        )


def ledger_from_sales(
    path: Path,
) -> Sequence[GeneralLedgerLineImpl[Any, Any]]:
    """
    Generate ledger from CSV files in the path.

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.

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
    df = read_all_dataframes(path / "sales")
    df["取引先"] = df["path"]
    df.fillna({"源泉徴収": 0, "手数料": 0}, inplace=True)

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
                        account="売上", amount=row["金額"], currency=row["通貨"]
                    ),
                ],
            )
        )
    for (_, date, currency), df_ in df.groupby(["取引先", "振込日", "通貨"]):
        amount = Decimal(df_["金額"].sum())
        if currency == "":
            withholding = Decimal(
                withholding_tax(df_.loc[df_["源泉徴収"] == True, "金額"].sum()).item()
            )
            values = [
                LedgerElementImpl(
                    account="事業主貸", amount=amount - withholding, currency=currency
                )
            ]
            if withholding > 0:
                values.append(
                    LedgerElementImpl(
                        account="仮払税金", amount=withholding, currency=currency
                    )
                )
        else:
            if (df_["源泉徴収"] == True).any():
                raise ValueError("通貨が異なる取引に源泉徴収が含まれています。")
            values = [
                LedgerElementImpl(account="事業主貸", amount=amount, currency=currency)
            ]
        ledger_lines.append(
            GeneralLedgerLineImpl(
                date=date,
                values=[
                    *values,
                    LedgerElementImpl(
                        account="売掛金", amount=-amount, currency=currency
                    ),
                ],
            )
        )
    if (df["発生日"] > df["振込日"]).any():
        raise ValueError("発生日が振込日より後の取引があります。")
    return ledger_lines
