from pathlib import Path

import typer
from rich import print

from ._main import generate_ledger

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def _main(path: Path) -> None:
    print(generate_ledger(path))
