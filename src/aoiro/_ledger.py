from collections.abc import Sequence
from decimal import Decimal
from itertools import chain
from typing import Callable, Protocol, TypeVar

import attrs
import pandas as pd
from account_codes_jp import Account, AccountSundry
from account_codes_jp._common import SUNDRY

Currency = TypeVar("Currency", bound=str)


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

    def __repr__(self) -> str:
        return (
            f"{self.date} {self.amount} {self.currency} "
            f"{self.debit_account} / {self.credit_account}"
        )


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
            .replace({pd.NaT: ""})
            .fillna("")
            .to_string(index=False, header=False)
        )


@attrs.frozen(kw_only=True, auto_detect=True)
class GeneralLedgerLineImpl(GeneralLedgerLine[Account, Currency]):
    date: pd.Timestamp
    values: Sequence[tuple[Account, Decimal, Currency]]


def generalledger_line_to_multiledger_line(
    line: GeneralLedgerLine[Account, Currency],
    is_debit: Callable[[Account], bool],
) -> MultiLedgerLine[Account, Currency]:
    debit = []
    credit = []
    for account, amount, currency in line.values:
        if is_debit(account):
            debit.append((account, amount, currency))
        else:
            credit.append((account, amount, currency))
    return MultiLedgerLineImpl(date=line.date, debit=debit, credit=credit)


def multiledger_line_to_generalledger_line(
    line: MultiLedgerLine[Account, Currency],
) -> GeneralLedgerLine[Account, Currency]:
    return GeneralLedgerLineImpl(
        date=line.date,
        values=[*line.debit, *line.credit],
    )


def multiledger_line_to_ledger_line(
    line: MultiLedgerLine[Account, Currency],
) -> Sequence[LedgerLine[Account | AccountSundry, Currency]]:
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
            credit_account=SUNDRY,
        )
        for debit_account, amount, currency in line.debit
    ] + [
        LedgerLineImpl(
            date=line.date,
            amount=amount,
            currency=currency,
            debit_account=SUNDRY,
            credit_account=credit_account,
        )
        for credit_account, amount, currency in line.credit
    ]


def generalledger_to_multiledger(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
    is_debit: Callable[[Account], bool],
) -> Sequence[MultiLedgerLine[Account, Currency]]:
    return [generalledger_line_to_multiledger_line(line, is_debit) for line in lines]


def multiledger_to_ledger(
    lines: Sequence[MultiLedgerLine[Account, Currency]],
) -> Sequence[LedgerLine[Account | AccountSundry, Currency]]:
    return list(chain(*[multiledger_line_to_ledger_line(line) for line in lines]))
