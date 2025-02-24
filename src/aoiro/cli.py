from pathlib import Path

import typer

from ._main import generate_ledger

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def _main(path: Path) -> None:
    generate_ledger(path)
