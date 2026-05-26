"""Click CLI for Medium.com."""

from __future__ import annotations

import sys

import click
from medium_cli.client import MediumClient
from rich.console import Console
from rich.table import Table

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Medium CLI — search and browse Medium.com from the terminal."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("tag")
def search(tag: str) -> None:
    """Search Medium articles by tag."""
    client = _get_client()
    try:
        articles = client.search_tag(tag)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not articles:
        console.print(f"[yellow]No articles found for tag '{tag}'.[/yellow]")
        return

    table = Table(title=f"Articles tagged '{tag}'")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Date")

    for i, a in enumerate(articles, 1):
        date_str = a.published_at.strftime("%Y-%m-%d") if a.published_at else ""
        table.add_row(str(i), a.title, a.author, date_str)

    console.print(table)


@main.command()
@click.argument("username")
def user(username: str) -> None:
    """Show a Medium user's profile and recent articles."""
    client = _get_client()
    try:
        user_obj, articles = client.get_user_articles(username)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Profile
    console.print(f"\n[bold]{user_obj.name}[/bold] ({user_obj.username})")
    console.print(f"  {user_obj.url}")
    if user_obj.bio:
        console.print(f"  [dim]{user_obj.bio}[/dim]")
    console.print()

    # Articles
    if not articles:
        console.print("[yellow]No articles found.[/yellow]")
        return

    table = Table(title="Recent Articles")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title")
    table.add_column("Date")
    table.add_column("Tags")

    for i, a in enumerate(articles, 1):
        date_str = a.published_at.strftime("%Y-%m-%d") if a.published_at else ""
        tags_str = ", ".join(a.tags) if a.tags else ""
        table.add_row(str(i), a.title, date_str, tags_str)

    console.print(table)


@main.command()
@click.argument("url")
def read(url: str) -> None:
    """Read a Medium article by URL.

    Fetches the full article content from the author's RSS feed
    and displays it cleaned and formatted.
    """
    client = _get_client()
    try:
        article, content = client.get_article(url)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    console.print(f"\n[bold]{article.title}[/bold]")
    console.print(f"[dim]by {article.author}[/dim]")
    if article.published_at:
        console.print(f"[dim]{article.published_at.strftime('%Y-%m-%d')}[/dim]")
    console.print()

    # Print content with wrapped paragraphs
    for para in content.split("\n"):
        para = para.strip()
        if para:
            console.print(para)
            console.print()


@main.command()
def trending() -> None:
    """Show trending/popular articles on Medium."""
    client = _get_client()
    try:
        articles = client.get_trending()
    except ConnectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not articles:
        console.print("[yellow]No trending articles found.[/yellow]")
        return

    table = Table(title="Trending on Medium")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Date")

    for i, a in enumerate(articles, 1):
        date_str = a.published_at.strftime("%Y-%m-%d") if a.published_at else ""
        table.add_row(str(i), a.title, a.author, date_str)

    console.print(table)


def _get_client() -> MediumClient:
    """Create a MediumClient instance."""
    return MediumClient()
