from pathlib import Path

# from rich import print
import attrs
import pandas as pd
import typer

from ._expenses import ledger_from_expenses
from ._ledger import multiledger_to_ledger
from ._multidimensional import multidimensional_ledger_to_ledger
from ._sales import ledger_from_sales

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def _main(path: Path) -> None:
    multilledger_vec = list(ledger_from_sales(path)) + list(ledger_from_expenses(path))
    multiledger = multidimensional_ledger_to_ledger(multilledger_vec)
    ledger = multiledger_to_ledger(multiledger)
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(
            pd.DataFrame([attrs.asdict(line) for line in ledger])  # type: ignore
            .set_index("date")
            .sort_index(axis=0)
        )
