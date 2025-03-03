from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

import numpy as np
import pandas as pd
import requests

from ._ledger import Account, Currency, GeneralLedgerLine, GeneralLedgerLineImpl


def get_currency(
    lines: Sequence[GeneralLedgerLine[Account, Currency]],
) -> Sequence[Currency]:
    return np.unique([x[2] for line in lines for x in line.values])  # type: ignore


def get_prices(
    currency: Iterable[Currency],
) -> Mapping[Currency, "pd.Series[Decimal]"]:
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
) -> Sequence[
    GeneralLedgerLineImpl[Account | Literal["為替差損益"], Currency | Literal[""]]
]:
    # get prices
    lines = sorted(lines, key=lambda x: x.date)
    currency = get_currency(lines)
    prices_ = dict(prices)
    del prices
    prices_.update(get_prices(set(currency) - set(prices_.keys())))

    balance: dict[Account, dict[Currency, list[tuple[Decimal, Decimal]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    # Balance of (account, currency) represented by tuple (price, amount)
    lines_new = []
    for line in lines:
        profit = Decimal(0)
        values: list[
            tuple[Account | Literal["為替差損益"], Decimal, Currency | Literal[""]]
        ] = []
        for a, v, c in line.values:
            if c == "":
                values.append((a, v, c))
                continue
            price_current = Decimal(str(prices_[c][line.date]))
            price_real = Decimal(0)
            if a in balance.keys():
                while v > 0:
                    vtemp = max(v, balance[a][c][0][1])
                    price_real += vtemp * balance[a][c][0][0]
                    v -= vtemp

                    # update balance
                    balance[a][c][0] = (
                        balance[a][c][0][0],
                        balance[a][c][0][1] - vtemp,
                    )
                    if balance[a][c][0][1] == 0:
                        balance[a][c].pop(0)
            else:
                balance[a][c].append((price_current, v))
                price_real = v * price_current
            values.append((a, price_real, ""))
            if is_debit(a) is True:
                profit += price_real
            else:
                profit -= price_real

        if profit != 0:
            values.append(("為替差損益", profit, ""))
        lines_new.append(GeneralLedgerLineImpl(date=line.date, values=values))
    return lines_new
