from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from decimal import ROUND_DOWN, Decimal, localcontext
from pathlib import Path
from typing import Callable, Literal

import numpy as np
import pandas as pd
import requests

from ._ledger import (
    Account,
    Currency,
    GeneralLedgerLine,
    GeneralLedgerLineImpl,
    LedgerElement,
    LedgerElementImpl,
)


def get_currency(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
) -> Sequence[Currency]:
    return np.unique([x.currency for line in lines for x in line.values])


def get_prices(
    currency: Iterable[Currency],
) -> Mapping[Currency, "pd.Series[Decimal]"]:
    """
    Get prices of the currency indexed by date (not datetime).

    Interpolates missing dates by forward fill.

    Parameters
    ----------
    currency : Iterable[Currency]
        The currency to get prices.

    Returns
    -------
    Mapping[Currency, pd.Series[Decimal]]
        The prices, indexed by date.

    """
    URL = "https://www.mizuhobank.co.jp/market/quote.csv"
    Path("~/.cache/aoiro").expanduser().mkdir(exist_ok=True)
    path = Path("~/.cache/aoiro/quote.csv").expanduser()
    if not path.exists():
        with path.open("w", encoding="utf-8") as f:
            r = requests.get(URL, timeout=5)
            r.encoding = "Shift_JIS"
            f.write(r.text)
    df = pd.read_csv(
        path, index_col=0, skiprows=2, na_values=["*****"], parse_dates=True
    )
    # fill missing dates
    df = df.reindex(pd.date_range(df.index[0], df.index[-1]), method="ffill")
    return df


def multidimensional_ledger_to_ledger(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
    is_debit: Callable[[Account], bool],
    prices: Mapping[Currency, "pd.Series[Decimal]"] = {},
) -> Sequence[GeneralLedgerLineImpl[Account | Literal["為替差損益"], Literal[""]]]:
    """
    Convert multidimensional ledger to ledger.

    The multidimensional ledger's any account must have
    positive amount. You may have 2 options:

    1.  Use the entire ledger as the input.
    2.  Add a general ledger line with only positive amounts,
        which represents the B/S sheet of the previous period, like
    >>> lines.append(
    >>>    GeneralLedgerLineImpl(
    >>>        date=datetime(2024, 1, 1),
    >>>        values=[
    >>>            ("現金", 1000, "JPY"),
    >>>            # don't add something like ("現金繰入", 1000, "JPY")
    >>>            # although this looks weird.
    >>>         ]
    >>>     )
    >>> )

    Returns
    -------
    GeneralLedgerLineImpl[Account | Literal["為替差損益"], Literal[""]]
        The ledger lines.

    """
    # get prices, use prices_
    lines = sorted(lines, key=lambda x: x.date)
    prices_ = dict(prices)
    del prices
    prices_.update(get_prices(set(get_currency(lines)) - set(prices_.keys())))

    # balance of (account, currency) represented by tuple (price, amount)
    balance: dict[Account, dict[Currency, list[tuple[Decimal, Decimal]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    # the new lines
    lines_new = []
    for line in lines:
        # profit of the old line
        profit = Decimal(0)

        # the values of the new line
        values: list[LedgerElement[Account | Literal["為替差損益"], Literal[""]]] = []

        # iterate over the values of the old line
        for el in line.values:
            amount_left = el.amount
            # skip if the currency is empty (default, exchange rate = 1)
            if el.currency == "":
                values.append(el)  # type: ignore
                continue

            # meaning of "quote": https://docs.ccxt.com/#/?id=market-structure
            price_current = Decimal(str(prices_[el.currency][line.date]))
            amount_in_quote = Decimal(0)
            if amount_left < 0:
                while amount_left < 0:
                    # the maximum amount to subtract from the first element
                    # of the balance[account][currency]
                    amount_substract = max(
                        -amount_left, balance[el.account][el.currency][0][1]
                    )
                    amount_in_quote -= (
                        amount_substract * balance[el.account][el.currency][0][0]
                    )
                    amount_left += amount_substract

                    # subtract the amount from the balance
                    balance[el.account][el.currency][0] = (
                        balance[el.account][el.currency][0][0],
                        balance[el.account][el.currency][0][1] - amount_substract,
                    )
                    # remove if the amount is zero
                    if balance[el.account][el.currency][0][1] == 0:
                        balance[el.account][el.currency].pop(0)
            else:
                balance[el.account][el.currency].append((price_current, amount_left))
                amount_in_quote = amount_left * price_current

            # round the amount_in_quote
            with localcontext() as ctx:
                ctx.rounding = ROUND_DOWN
                amount_in_quote = round(amount_in_quote, 0)

            # append to the values of the new line
            values.append(
                LedgerElementImpl(
                    account=el.account, amount=amount_in_quote, currency=""
                )
            )

            # add to the profit
            if is_debit(el.account) is True:
                profit += amount_in_quote
            else:
                profit -= amount_in_quote

        # append only if profit is not zero
        if profit != 0:
            values.append(
                LedgerElementImpl(account="為替差損益", amount=profit, currency="")
            )

        # append the new line
        lines_new.append(GeneralLedgerLineImpl(date=line.date, values=values))
    return lines_new
