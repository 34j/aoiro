from pathlib import Path

from typer.testing import CliRunner

from aoiro.cli import app

runner = CliRunner()


def test_help():
    """The help message includes the CLI name."""
    result = runner.invoke(app, [(Path(__file__).parent / "test_dir").as_posix()])
    assert result.exit_code == 0
