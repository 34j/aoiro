import re
import warnings
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from dateparser import parse

from .._ledger import GeneralLedgerLineImpl, LedgerElementImpl


def read_all_csvs(path: Path, /, **kwargs: Any) -> pd.DataFrame:
    """
    Read all CSV files in the path.

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.
    **kwargs : Any
        The keyword arguments for `pd.read_csv`.

    Returns
    -------
    pd.DataFrame
        The concatenated DataFrame with
        column "path" containing the relative path of the CSV file added.

    """
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p, **kwargs)
        df["path"] = p.relative_to(path).as_posix()
        dfs.append(df)
    if not dfs:
        return pd.DataFrame(columns=["path"])
    return pd.concat(dfs)


def parse_date(s: str) -> pd.Timestamp:
    """
    Parse date.

    Prefer the last day of the month if the day is not provided.

    Parameters
    ----------
    s : str
        The string to parse.

    Returns
    -------
    pd.Timestamp
        The parsed date.

    """
    return pd.Timestamp(parse(s, settings={"PREFER_DAY_OF_MONTH": "last"}))


def parse_money(
    s: str, currency: str | None = None
) -> tuple[Decimal | None, str | None]:
    """
    Parse money.

    Parameters
    ----------
    s : str
        The string to parse.
    currency : str | None, optional
        The currency, by default None.
        If provided, the currency
        in the string would be ignored and replaced by this.

    Returns
    -------
    tuple[Decimal | None, str | None]
        The amount and the currency.

    """
    match = re.search(r"[\d.]+", s)
    if match is None:
        return None, None
    amount = Decimal(match.group())
    if currency is None:
        currency = re.sub(r"\s+", "", s[: match.start()] + s[match.end() :])
    return amount, currency


def read_simple_csvs(path: Path) -> pd.DataFrame:
    """
    Read all CSV files in the path.

    The CSV files are assumed to have columns
    ["発生日", "金額"].

    Parameters
    ----------
    path : Path
        The path to the directory containing CSV files.

    Returns
    -------
    pd.DataFrame
        The concatenated DataFrame with columns
        ["発生日", "金額", "通貨", "path"].

    """
    df = read_all_csvs(path, dtype=str)
    for col in ["発生日", "金額"]:
        if col not in df.columns:
            df[col] = None

    # parse date
    for k in df.columns:
        if "日" not in k:
            continue
        df[k] = df[k].map(parse_date)

    # parse money
    df[["金額", "通貨"]] = pd.DataFrame(
        df["金額"].map(parse_money).tolist(), index=df.index
    )

    # set date as index
    df.set_index("発生日", inplace=True, drop=False)
    return df


def read_general_ledger(path: Path) -> Iterable[GeneralLedgerLineImpl[Any, Any]]:
    """
    Read general ledger.

    The first column is assumed to be the date.
    For all n in N. the 2n-1-th column is assumed to be
    the account name, and the 2n-th column
    is assumed to be the amount.

    Parameters
    ----------
    path : Path
        The path to the CSV file.

    Returns
    -------
    Iterable[GeneralLedgerLineImpl[Any, Any]]
        The general ledger.

    """
    df = read_all_csvs(path / "general", header=None, dtype=str)
    df.drop(columns="path", inplace=True)
    if df.empty:
        return
    if len(df.columns) % 2 != 1:
        raise ValueError("The number of columns should be odd.")
    if len(df.columns) < 3:
        raise ValueError("The number of columns should be at least 3.")
    for _, row in df.iterrows():
        values: list[LedgerElementImpl[Any, Any]] = []
        for i in range(1, len(row), 2):
            amount, currency = parse_money(row[i + 1])
            if amount is None:
                warnings.warn(f"Amount not found in {row[i + 1]}", stacklevel=2)
                continue
            values.append(
                LedgerElementImpl(
                    account=row[i],
                    amount=amount,
                    currency=currency,
                )
            )
        yield GeneralLedgerLineImpl(
            values=values,
            date=parse_date(row[0]),
        )
