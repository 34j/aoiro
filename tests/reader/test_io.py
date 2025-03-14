from decimal import Decimal

import pandas as pd

from aoiro.reader._io import parse_date, parse_money


def test_parse_date():
    assert parse_date("2021-01") == pd.Timestamp("2021-01-31")


def test_parse_money():
    assert parse_money("1000.1") == (Decimal("1000.1"), "")
    assert parse_money("1000.1円") == (Decimal("1000.1"), "円")
    assert parse_money("$ 1000.1    USD") == (Decimal("1000.1"), "$USD")
    assert parse_money("1000.1 AUD", "USD") == (Decimal("1000.1"), "USD")
