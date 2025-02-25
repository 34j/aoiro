from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from ._ledger import (
    Account,
    Currency,
    MultiLedgerLine,
)


def get_currency(
    lines: Sequence[MultiLedgerLine[Account, Currency]],
) -> Sequence[Currency]:
    return np.unique(
        [x[2] for line in lines for el in [line.debit, line.credit] for x in el]
    )


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
    lines: Sequence[MultiLedgerLine[Account, Currency]],
    prices: Mapping[Currency, "pd.Series[Decimal]"] = {},
) -> Sequence[MultiLedgerLine[Account, Currency]]:
    # get prices
    lines = sorted(lines, key=lambda x: x.date)
    currency = get_currency(lines)
    prices_ = dict(prices)
    del prices
    prices_.update(get_prices(set(currency) - set(prices_.keys())))

    debit_balance: dict[Account, dict[Currency, list[tuple[Decimal, Decimal]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    credit_balance: dict[Account, dict[Currency, list[tuple[Decimal, Decimal]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for line in lines:
        for a, v, c in line.debit:
            if c == "":
                continue
            if a in credit_balance.keys():
                while v != 0:
                    vtemp = max(v, credit_balance[a][c][0][1])
                    v -= vtemp
                    credit_balance[a][c][0] = (
                        credit_balance[a][c][0][0],
                        credit_balance[a][c][0][1] - vtemp,
                    )
                    if credit_balance[a][c][0][1] == 0:
                        credit_balance[a][c].pop(0)
            else:
                credit_balance[a][c].append((prices_[c][line.date], v))
        for a, d, c in line.credit:
            if c == "":
                continue
            if a in debit_balance.keys():
                while d != 0:
                    dtemp = max(d, debit_balance[a][c][0][1])
                    d -= dtemp
                    debit_balance[a][c][0] = (
                        debit_balance[a][c][0][0],
                        debit_balance[a][c][0][1] - dtemp,
                    )
                    if debit_balance[a][c][0][1] == 0:
                        debit_balance[a][c].pop(0)
            else:
                debit_balance[a][c].append((prices_[c][line.date], d))
    return lines
