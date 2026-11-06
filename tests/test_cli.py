from decimal import Decimal
from pathlib import Path

import pandas as pd

from aoiro.cli import app


def test_run(monkeypatch):
    """The help message includes the CLI name."""
    dates = pd.date_range("2023-12-01", "2024-03-31")
    prices = pd.Series([Decimal(1)] * len(dates), index=dates)
    monkeypatch.setattr(
        "aoiro._multidimensional.get_prices",
        lambda currencies: dict.fromkeys(currencies, prices),
    )
    app([(Path(__file__).parent / "test_dir").as_posix(), "--years", "2024"])
