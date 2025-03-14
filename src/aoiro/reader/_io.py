from decimal import Decimal
from pathlib import Path

import pandas as pd
from dateparser import parse


def read_all_dataframes(path: Path) -> pd.DataFrame:
    dfs = []
    for p in path.rglob("*.csv"):
        df = pd.read_csv(p)
        df["path"] = p.relative_to(path).as_posix()
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
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
