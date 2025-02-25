from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ._ledger import MultiLedgerLine, MultiLedgerLineImpl, read_all_dataframes


def ledger_from_expenses(
    path: Path,
) -> Sequence[MultiLedgerLine[Any, Any]]:
    df = read_all_dataframes(path / "expenses")
    df["取引先"] = df["path"]
    res = []
    for d, row in df.iterrows():
        res.append(
            MultiLedgerLineImpl(
                date=d,
                debit=[("事業主貸", row["金額"], row["通貨"])],
                credit=[("売上", row["金額"], row["通貨"])],
            )
        )
    return res
