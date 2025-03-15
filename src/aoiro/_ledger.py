from collections.abc import Sequence
from decimal import Decimal
from itertools import chain
from typing import Any, Callable, Literal, Protocol, TypeVar

import attrs
import pandas as pd
from account_codes_jp._common import SUNDRY

AccountSundry = Literal["諸口"]
Account = TypeVar("Account", bound=str)
Currency = TypeVar("Currency", bound=str)


class _LedgerLineBase(Protocol):
    date: pd.Timestamp
    """The date when the transaction occurred."""


class LedgerLine(_LedgerLineBase, Protocol[Account, Currency]):
    amount: Decimal
    """The amount. Must be non-negative."""
    currency: Currency
    """The currency."""
    debit_account: Account
    """The account written on the debit side."""
    credit_account: Account
    """The account written on the credit side."""


class LedgerElement(Protocol[Account, Currency]):
    account: Account
    """The account."""
    amount: Decimal
    """The amount."""
    currency: Currency
    """The currency."""


class MultiLedgerLine(_LedgerLineBase, Protocol[Account, Currency]):
    debit: Sequence[LedgerElement[Account, Currency]]
    """The accounts and amounts on the debit side.
    Each amount needs to be non-negative."""
    credit: Sequence[LedgerElement[Account, Currency]]
    """The accounts and amounts on the credit side.
    Each amount needs to be non-negative."""


class GeneralLedgerLine(_LedgerLineBase, Protocol[Account, Currency]):
    values: Sequence[LedgerElement[Account, Currency]]
    """The accounts and amounts. Amounts does not need to be non-negative."""


@attrs.frozen(kw_only=True)
class LedgerLineImpl(LedgerLine[Account, Currency]):
    date: pd.Timestamp
    amount: Decimal = attrs.field()
    currency: Currency
    debit_account: Account
    credit_account: Account

    def __repr__(self) -> str:
        return (
            f"{self.date} {self.amount} {self.currency} "
            f"{self.debit_account} / {self.credit_account}"
        )

    @amount.validator
    def _validate_amount(self, attribute: Any, value: Decimal) -> None:
        if value < Decimal(0):
            raise ValueError("amount must be non-negative")


@attrs.frozen(kw_only=True)
class LedgerElementImpl(LedgerElement[Account, Currency]):
    account: Account
    amount: Decimal
    currency: Currency

    def __repr__(self) -> str:
        return f"{self.account} {self.amount} {self.currency}"


@attrs.frozen(kw_only=True, auto_detect=True)
class MultiLedgerLineImpl(MultiLedgerLine[Account, Currency]):
    date: pd.Timestamp
    debit: Sequence[LedgerElement[Account, Currency]] = attrs.field()
    credit: Sequence[LedgerElement[Account, Currency]] = attrs.field()

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

    @debit.validator
    def _validate_debit(
        self, attribute: Any, value: Sequence[LedgerElement[Account, Currency]]
    ) -> None:
        if any(el.amount < Decimal(0) for el in value):
            raise ValueError("amount must be non-negative")

    @credit.validator
    def _validate_credit(
        self, attribute: Any, value: Sequence[LedgerElement[Account, Currency]]
    ) -> None:
        if any(el.amount < Decimal(0) for el in value):
            raise ValueError("amount must be non-negative")


@attrs.frozen(kw_only=True, auto_detect=True)
class GeneralLedgerLineImpl(GeneralLedgerLine[Account, Currency]):
    date: pd.Timestamp
    values: Sequence[LedgerElement[Account, Currency]]


def generalledger_line_to_multiledger_line(
    line: GeneralLedgerLine[Account, Currency], is_debit: Callable[[Account], bool], /
) -> MultiLedgerLine[Account, Currency]:
    """
    Convert a GeneralLedgerLine to a MultiLedgerLine.

    Parameters
    ----------
    line : GeneralLedgerLine[Account, Currency]
        The GeneralLedgerLine to convert.
    is_debit : Callable[[Account], bool]
        Whether the account is a debit account.

    Returns
    -------
    MultiLedgerLine[Account, Currency]
        The converted MultiLedgerLine.

    """
    debit = []
    credit = []
    for el in line.values:
        if is_debit(el.account) == (el.amount > 0):
            debit.append(
                LedgerElementImpl(
                    account=el.account, amount=abs(el.amount), currency=el.currency
                )
            )
        else:
            credit.append(
                LedgerElementImpl(
                    account=el.account, amount=abs(el.amount), currency=el.currency
                )
            )
    return MultiLedgerLineImpl(date=line.date, debit=debit, credit=credit)


def multiledger_line_to_generalledger_line(
    line: MultiLedgerLine[Account, Currency], /
) -> GeneralLedgerLine[Account, Currency]:
    """
    Convert a MultiLedgerLine to a GeneralLedgerLine.

    Parameters
    ----------
    line : MultiLedgerLine[Account, Currency]
        The MultiLedgerLine to convert.

    Returns
    -------
    GeneralLedgerLine[Account, Currency]
        The converted GeneralLedgerLine.

    """
    return GeneralLedgerLineImpl(
        date=line.date,
        values=[*line.debit, *line.credit],
    )


def multiledger_line_to_ledger_line(
    line: MultiLedgerLine[Account, Currency], /
) -> Sequence[LedgerLine[Account | AccountSundry, Currency]]:
    """
    Convert a MultiLedgerLine to a list of LedgerLine.

    Parameters
    ----------
    line : MultiLedgerLine[Account, Currency]
        The MultiLedgerLine to convert.

    Returns
    -------
    Sequence[LedgerLine[Account | AccountSundry, Currency]]
        The converted LedgerLines.

    """
    if (
        len(line.debit) == len(line.credit) == 1
        and line.debit[0].amount == line.credit[0].amount
        and line.debit[0].currency == line.credit[0].currency
    ):
        return [
            LedgerLineImpl(
                date=line.date,
                amount=line.debit[0].amount,
                currency=line.debit[0].currency,
                debit_account=line.debit[0].account,
                credit_account=line.credit[0].account,
            )
        ]
    return [
        LedgerLineImpl(
            date=line.date,
            amount=el.amount,
            currency=el.currency,
            debit_account=el.account,
            credit_account=SUNDRY,
        )
        for el in line.debit
    ] + [
        LedgerLineImpl(
            date=line.date,
            amount=el.amount,
            currency=el.currency,
            debit_account=SUNDRY,
            credit_account=el.account,
        )
        for el in line.credit
    ]


def generalledger_to_multiledger(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
    is_debit: Callable[[Account], bool],
) -> Sequence[MultiLedgerLine[Account, Currency]]:
    """
    Convert a GeneralLedger to a MultiLedger.

    Parameters
    ----------
    lines : Sequence[GeneralLedgerLine[Account, Currency]]
        The GeneralLedger to convert.
    is_debit : Callable[[Account], bool]
        Whether the account is a debit account.

    Returns
    -------
    Sequence[MultiLedgerLine[Account, Currency]]
        The converted MultiLedger.

    """
    return [generalledger_line_to_multiledger_line(line, is_debit) for line in lines]


def multiledger_to_generalledger(
    lines: Sequence[MultiLedgerLine[Account, Currency]],
) -> Sequence[GeneralLedgerLine[Account, Currency]]:
    """
    Convert a MultiLedger to a GeneralLedger.

    Parameters
    ----------
    lines : Sequence[MultiLedgerLine[Account, Currency]]
        The MultiLedger to convert.

    Returns
    -------
    Sequence[GeneralLedgerLine[Account, Currency]]
        The converted GeneralLedger.

    """
    return [multiledger_line_to_generalledger_line(line) for line in lines]


def multiledger_to_ledger(
    lines: Sequence[MultiLedgerLine[Account, Currency]],
) -> Sequence[LedgerLine[Account | AccountSundry, Currency]]:
    """
    Convert a MultiLedger to a Ledger.

    Parameters
    ----------
    lines : Sequence[MultiLedgerLine[Account, Currency]]
        The MultiLedger to convert.

    Returns
    -------
    Sequence[LedgerLine[Account | AccountSundry, Currency]]
        The converted Ledger.

    """
    return list(chain(*[multiledger_line_to_ledger_line(line) for line in lines]))
