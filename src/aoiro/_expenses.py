from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from ._io import read_all_dataframes
from ._ledger import (
    GeneralLedgerLineImpl,
)


def ledger_from_expenses(
    path: Path,
) -> Sequence[GeneralLedgerLineImpl[Literal["事業主貸", "売上"], Any]]:
    df = read_all_dataframes(path / "expenses")
    df["取引先"] = df["path"]
    res: list[GeneralLedgerLineImpl[Literal["事業主貸", "売上"], Any]] = []
    for d, row in df.iterrows():
        res.append(
            GeneralLedgerLineImpl(
                date=d,
                values=[
                    ("事業主貸", row["金額"], row["通貨"]),
                    ("売上", row["金額"], row["通貨"]),
                ],
            )
        )
    return res
