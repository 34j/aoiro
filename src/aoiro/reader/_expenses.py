from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .._ledger import GeneralLedgerLineImpl, LedgerElementImpl
from ._io import read_simple_csvs


def ledger_from_expenses(
    path: Path,
) -> Sequence[GeneralLedgerLineImpl[Any, Any]]:
    """
    Generate ledger from expenses.

    The CSV files are assumed to have columns
    ["勘定科目"].
    The relative path of the CSV file would be used as "取引先".

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.

    Returns
    -------
    Sequence[GeneralLedgerLineImpl[Any, Any]]
        The ledger lines.

    """
    df = read_simple_csvs(path / "expenses")
    if df.empty:
        return []
    df["取引先"] = df["path"]
    res: list[GeneralLedgerLineImpl[Any, Any]] = []
    for date, row in df.iterrows():
        res.append(
            GeneralLedgerLineImpl(
                date=date,
                values=[
                    LedgerElementImpl(
                        account="事業主借", amount=row["金額"], currency=row["通貨"]
                    ),
                    LedgerElementImpl(
                        account=row["勘定科目"],
                        amount=row["金額"],
                        currency=row["通貨"],
                    ),
                ],
            )
        )
    return res
