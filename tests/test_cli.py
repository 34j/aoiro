from pathlib import Path

from aoiro.cli import app


def test_run():
    """The help message includes the CLI name."""
    app([(Path(__file__).parent / "test_dir").as_posix()])
