"""The entry point, and the top level commands that do not belong to a group."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from holdtrim import __version__
from holdtrim.cli import (
    cargo,
    fleetcmd,
    flights,
    messages,
    planning,
    reports,
    sheets,
    stations,
    tails,
    ulds,
)
from holdtrim.cli.common import (
    DEFAULT_BOOK,
    Settings,
    exit_code_for,
    opened_book,
    settings,
)
from holdtrim.errors import HoldtrimError
from holdtrim.store.book import initialise


@click.group()
@click.option(
    "--book",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_BOOK,
    envvar="HOLDTRIM_BOOK",
    show_default=True,
    help="The SQLite book to work on.",
)
@click.version_option(__version__, prog_name="holdtrim")
@click.pass_context
def cli(ctx: click.Context, book: Path) -> None:
    """Load control for a regional freighter operation."""
    ctx.obj = Settings(book=book)


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Create the book, or bring an existing one up to date."""
    path = settings(ctx).book
    existed = path.exists()
    initialise(path)
    click.echo(f"{'brought up to date' if existed else 'created'} {path}")


@cli.command()
@click.pass_context
def about(ctx: click.Context) -> None:
    """Say what this build is and what book it is pointed at."""
    click.echo(f"holdtrim {__version__}")
    click.echo(f"book {settings(ctx).book}")


@cli.group()
def book() -> None:
    """Look after the book itself."""


@book.command("counts")
@click.pass_context
def book_counts(ctx: click.Context) -> None:
    """How many rows are in each table worth counting."""
    with opened_book(ctx) as opened:
        for table, count in opened.counts().items():
            click.echo(f"{table} {count}")


@book.command("verify")
@click.pass_context
def book_verify(ctx: click.Context) -> None:
    """Check the file over and report anything wrong with it."""
    with opened_book(ctx) as opened:
        problems = opened.verify()
    if not problems:
        click.echo("the book is sound")
        return
    for problem in problems:
        click.echo(f"problem: {problem}")
    raise SystemExit(7)


@book.command("backup")
@click.argument("destination", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def book_backup(ctx: click.Context, destination: Path) -> None:
    """Copy the book somewhere safe."""
    with opened_book(ctx) as opened:
        opened.backup(destination)
    click.echo(f"copied to {destination}")


cli.add_command(cargo.group)
cli.add_command(fleetcmd.group)
cli.add_command(flights.group)
cli.add_command(messages.group)
cli.add_command(planning.group)
cli.add_command(reports.group)
cli.add_command(sheets.group)
cli.add_command(stations.group)
cli.add_command(tails.group)
cli.add_command(ulds.group)


def run() -> None:
    """The console script, which turns a refusal into an exit status."""
    try:
        cli.main(standalone_mode=False)
    except HoldtrimError as error:
        click.echo(f"error: {error}", err=True)
        sys.exit(exit_code_for(error))
    except click.ClickException as error:
        error.show()
        sys.exit(error.exit_code)
    except click.Abort:
        click.echo("stopped", err=True)
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    run()
