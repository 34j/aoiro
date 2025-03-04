from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ._io import read_all_dataframes
from ._ledger import GeneralLedgerLineImpl, LedgerElementImpl


def ledger_from_expenses(
    path: Path,
) -> Sequence[GeneralLedgerLineImpl[Any, Any]]:
    df = read_all_dataframes(path / "expenses")
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
