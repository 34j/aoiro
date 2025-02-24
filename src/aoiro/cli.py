from pathlib import Path

import pandas as pd
import typer
from rich import print

from ._main import generate_ledger, multiledger_to_ledger

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def _main(path: Path) -> None:
    print(pd.DataFrame(multiledger_to_ledger(generate_ledger(path))))
