from collections.abc import Sequence
from decimal import Decimal
from itertools import chain
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

import attrs
import numpy as np
import pandas as pd
from dateparser import parse
from numpy.typing import NDArray

Currency = TypeVar("Currency")
Account = TypeVar("Account")


class LedgerLine(Protocol[Account, Currency]):
    date: pd.Timestamp
    amount: Decimal
    currency: Currency
    debit_account: Account
    credit_account: Account


class MultiLedgerLine(Protocol[Account, Currency]):
    date: pd.Timestamp
    debit: Sequence[tuple[Account, Decimal, Currency]]
    credit: Sequence[tuple[Account, Decimal, Currency]]


@attrs.frozen(kw_only=True)
class LedgerLineImpl(LedgerLine[Account, Currency]):
    date: pd.Timestamp
    amount: Decimal
    currency: Currency
    debit_account: Account
    credit_account: Account


@attrs.frozen(kw_only=True, auto_detect=True)
class MultiLedgerLineImpl(MultiLedgerLine[Account, Currency]):
    date: pd.Timestamp
    debit: Sequence[tuple[Account, Decimal, Currency]]
    credit: Sequence[tuple[Account, Decimal, Currency]]


def multiledger_line_to_ledger_line(
    line: MultiLedgerLine[Account, Currency],
) -> Sequence[LedgerLine[Account | Literal["諸口"], Currency]]:
    if len(line.debit) == len(line.credit) == 1:
        return [
            LedgerLineImpl(
                date=line.date,
                amount=line.debit[0][1],
                currency=line.debit[0][2],
                debit_account=line.debit[0][0],
                credit_account=line.credit[0][0],
            )
        ]
    return [  # type: ignore
        LedgerLineImpl(
            date=line.date,
            amount=amount,
            currency=currency,
            debit_account=debit_account,
            credit_account="諸口",
        )
        for debit_account, amount, currency in line.debit
    ] + [
        LedgerLineImpl(
            date=line.date,
            amount=amount,
            currency=currency,
            debit_account="諸口",
            credit_account=credit_account,
        )
        for credit_account, amount, currency in line.credit
    ]


def multiledger_to_ledger(
    lines: Sequence[MultiLedgerLine[Account, Currency]],
) -> Sequence[LedgerLine[Account | Literal["諸口"], Currency]]:
    return list(chain(*[multiledger_line_to_ledger_line(line) for line in lines]))


def withholding_tax(amount: NDArray[Any]) -> NDArray[Any]:
    return np.floor(
        np.where(
            amount > 1000000,
            1000000 * Decimal("0.1021") + (amount - 1000000) * Decimal("0.2042"),
            amount * Decimal("0.1021"),
        )
    )


def generate_ledger(
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
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p)
        df["取引先"] = p.stem
        dfs.append(df)
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
        df["金額"]
        .astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
        .apply(lambda x: Decimal(str(x)))
    )
    df.fillna({"源泉徴収": 0, "手数料": 0}, inplace=True)
    df.set_index("発生日", inplace=True, drop=False)

    ledger_lines: list[MultiLedgerLine[Any, Any]] = []
    for d, row in df.iterrows():
        ledger_lines.append(
            MultiLedgerLineImpl(
                date=d,
                debit=[("事業主貸", row["金額"], row["通貨"])],
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
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(df)
        print(
            df[df["振込日"].dt.year == 2024]
            .groupby("取引先")[["金額", "源泉徴収"]]
            .sum()
        )
    return ledger_lines
