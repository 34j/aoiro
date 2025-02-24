from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, TypeVar

import pandas as pd
from dateparser import parse

Currency = TypeVar("Currency")
Account = TypeVar("Account")


class LedgerLine(Protocol[Account, Currency]):
    amount: Decimal
    currency: Currency
    debit_account: Account
    credit_account: Account


class MultiLedgerLine(Protocol[Account, Currency]):
    debit: Sequence[tuple[Account, Decimal, Currency]]
    credit: Sequence[tuple[Account, Decimal, Currency]]


def generate_ledger(path: Path) -> Sequence[MultiLedgerLine[Any, Any]]:
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
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p)
        df["取引先"] = p.stem
        dfs.append(df)
        print(df)
    df = pd.concat(dfs)
    del dfs
    for k in ["発生日", "振込日"]:
        df[k] = pd.to_datetime(
            df[k].map(lambda s: parse(s, settings={"PREFER_DAY_OF_MONTH": "last"}))
        )
    df["通貨"] = (
        df["金額"]
        .astype(str)
        .str.replace(r"[\d.]", "", regex=True)
        .replace("$", "USD", regex=False)
        .astype(str)
    )
    df["金額"] = (
        df["金額"].astype(str).str.replace(r"[^\d.]", "", regex=True).astype(float)
    )
    df.fillna({"源泉徴収": 0, "手数料": 0}, inplace=True)
    df.loc[df["源泉徴収"] == True, "源泉徴収"] = (
        df.loc[df["源泉徴収"] == True, "金額"].astype(float) * 10.21 / 100
    ).astype(int)
    df.set_index("発生日", inplace=True)
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(df)
        print(
            df[df.index.to_series().dt.year == 2024]
            .groupby("取引先")[["金額", "源泉徴収"]]
            .sum()
        )
    return []
