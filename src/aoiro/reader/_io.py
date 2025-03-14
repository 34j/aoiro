from decimal import Decimal
from pathlib import Path

import pandas as pd
from dateparser import parse


def read_csvs(path: Path) -> pd.DataFrame:
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
    # concat all CSV files in the path
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p)
        df["path"] = p.relative_to(path).as_posix()
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs)

    # parse the columns
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

    # set date as index
    df.set_index("発生日", inplace=True, drop=False)
    return df
