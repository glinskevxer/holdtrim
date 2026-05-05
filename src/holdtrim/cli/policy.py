"""Commands for the settings the operator may change."""

from __future__ import annotations

import click

from holdtrim.cli.common import echo_table, opened_book
from holdtrim.store import settings


@click.group("setting")
def group() -> None:
    """The figures that are policy rather than certificate."""


@group.command("list")
@click.pass_context
def listing(ctx: click.Context) -> None:
    """Every setting, its value, and where that value came from."""
    with opened_book(ctx) as book:
        found = settings.listing(book.connection)
    echo_table(
        ["setting", "value", "source", "what it means"],
        [
            [
                setting.name,
                value or "not set",
                "set" if was_set else "default",
                setting.meaning,
            ]
            for setting, value, was_set in found
        ],
        empty="no settings",
    )


@group.command("get")
@click.argument("name")
@click.pass_context
def get(ctx: click.Context, name: str) -> None:
    """One setting."""
    with opened_book(ctx) as book:
        setting = settings.known(name)
        click.echo(setting.describe(settings.text(book.connection, name)))


@group.command("set")
@click.argument("name")
@click.argument("value")
@click.pass_context
def put(ctx: click.Context, name: str, value: str) -> None:
    """Change one setting."""
    with opened_book(ctx) as book:
        settings.put(book.connection, name, value)
    click.echo(f"{settings.known(name).name} is now {value}")


@group.command("clear")
@click.argument("name")
@click.pass_context
def clear(ctx: click.Context, name: str) -> None:
    """Put a setting back to its default."""
    with opened_book(ctx) as book:
        settings.clear(book.connection, name)
        setting = settings.known(name)
    click.echo(f"{setting.name} is back to {setting.default or 'not set'}")
