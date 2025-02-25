from collections.abc import Mapping, Sequence
from decimal import Decimal
from itertools import chain
from pathlib import Path
from typing import Literal, Protocol, TypeVar

import attrs
import pandas as pd
from dateparser import parse

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


class GeneralLedgerLine(Protocol[Account, Currency]):
    date: pd.Timestamp
    values: Sequence[tuple[Account, Decimal, Currency]]


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

    def __repr__(self) -> str:
        date = pd.Series([self.date], name="date")
        debit = pd.DataFrame(
            self.debit, columns=["debit_account", "amount", "currency"]
        )
        credit = pd.DataFrame(
            self.credit, columns=["credit_account", "amount", "currency"]
        )
        return (
            pd.concat([date, debit, credit], axis=1)
            .fillna("")
            .to_string(index=False, header=False)
        )


@attrs.frozen(kw_only=True, auto_detect=True)
class GeneralLedgerLineImpl(GeneralLedgerLine[Account, Currency]):
    date: pd.Timestamp
    values: Sequence[tuple[Account, Decimal, Currency]]


def generalledger_line_to_multiledger_line(
    line: GeneralLedgerLine[Account, Currency],
    is_positive: Mapping[Account, bool],
) -> MultiLedgerLine[Account, Currency]:
    debit = []
    credit = []
    for account, amount, currency in line.values:
        if is_positive[account]:
            debit.append((account, amount, currency))
        else:
            credit.append((account, amount, currency))
    return MultiLedgerLineImpl(date=line.date, debit=debit, credit=credit)


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


def read_all_dataframes(path: Path) -> pd.DataFrame:
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p)
        df["path"] = p.relative_to(path).as_posix()
        dfs.append(df)
    df = pd.concat(dfs)
    for k in df.columns:
        if "日" not in k:
            continue
        df[k] = pd.to_datetime(
            df[k].map(lambda s: parse(s, settings={"PREFER_DAY_OF_MONTH": "last"}))
        )
    df["通貨"] = (
        df["金額"]
        .astype(str)
        .str.replace(r"[\d.]", "", regex=True)
        .str.strip()
        .str.replace("$", "USD", regex=False)
        .astype(str)
    )
    df["金額"] = (
        df["金額"]
        .astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
        .apply(lambda x: Decimal(str(x)))
    )
    df.set_index("発生日", inplace=True, drop=False)
    return df
