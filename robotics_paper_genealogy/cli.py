"""CLI interface for vision-paper-genealogy."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from robotics_paper_genealogy.graph.builder import build_graph, build_graph_from_domains
from robotics_paper_genealogy.models import load_all_domains, load_domain
from robotics_paper_genealogy.viz.tree import render_ancestors, render_method_detail, render_tree

app = typer.Typer(
    name="vision-paper-genealogy",
    help="Interactive genealogy tree visualizer for Computer Vision research methods.",
)
console = Console()

DEFAULT_DOMAINS_DIR = Path(__file__).parent.parent / "domains"


def _resolve_domains_dir(domains_dir: Path | None) -> Path:
    if domains_dir is not None:
        return domains_dir
    if DEFAULT_DOMAINS_DIR.exists():
        return DEFAULT_DOMAINS_DIR
    return Path.cwd() / "domains"


@app.command()
def show(
    domain: str | None = typer.Argument(None, help="Domain name (YAML filename without extension)"),
    domains_dir: Path | None = typer.Option(None, "--dir", "-d", help="Path to domains directory"),
) -> None:
    """Show the genealogy tree for a domain (or all domains)."""
    dir_path = _resolve_domains_dir(domains_dir)

    if domain:
        yaml_path = dir_path / f"{domain}.yaml"
        if not yaml_path.exists():
            console.print(f"[red]Domain file not found: {yaml_path}[/red]")
            raise typer.Exit(1)
        d = load_domain(yaml_path)
        console.print(f"\n[bold blue]{d.name}[/bold blue]")
        if d.description:
            console.print(f"[dim]{d.description}[/dim]")
        console.print()
        graph = build_graph(d)
        render_tree(graph, console)
    else:
        domains = load_all_domains(dir_path)
        if not domains:
            console.print(f"[red]No domain YAML files found in {dir_path}[/red]")
            raise typer.Exit(1)
        for d in domains:
            console.print(f"\n[bold blue]{d.name}[/bold blue]")
            if d.description:
                console.print(f"[dim]{d.description}[/dim]")
            console.print()
            graph = build_graph(d)
            render_tree(graph, console)


@app.command()
def ancestors(
    method: str = typer.Argument(..., help="Method name to trace ancestors"),
    domains_dir: Path | None = typer.Option(None, "--dir", "-d", help="Path to domains directory"),
) -> None:
    """Trace the ancestors of a method."""
    dir_path = _resolve_domains_dir(domains_dir)
    domains = load_all_domains(dir_path)
    graph = build_graph_from_domains(domains)
    render_ancestors(graph, method, console)


@app.command()
def info(
    method: str = typer.Argument(..., help="Method name to show details"),
    domains_dir: Path | None = typer.Option(None, "--dir", "-d", help="Path to domains directory"),
) -> None:
    """Show detailed information about a method."""
    dir_path = _resolve_domains_dir(domains_dir)
    domains = load_all_domains(dir_path)
    graph = build_graph_from_domains(domains)
    render_method_detail(graph, method, console)


@app.command(name="list")
def list_methods(
    domains_dir: Path | None = typer.Option(None, "--dir", "-d", help="Path to domains directory"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    year: int | None = typer.Option(None, "--year", "-y", help="Filter by year"),
) -> None:
    """List all methods across all domains."""
    dir_path = _resolve_domains_dir(domains_dir)
    domains = load_all_domains(dir_path)

    for d in domains:
        methods = d.methods
        if tag:
            methods = [m for m in methods if tag in m.tags]
        if year:
            methods = [m for m in methods if m.year == year]

        if not methods:
            continue

        console.print(f"\n[bold blue]{d.name}[/bold blue]")
        for m in sorted(methods, key=lambda x: x.year):
            stars = f" \u2605{m.stars:,}" if m.stars else ""
            code = " \U0001f4e6" if m.code else ""
            tags = f" [{', '.join(m.tags)}]" if m.tags else ""
            console.print(f"  {m.name} [{m.year}]{stars}{code}{tags}")


if __name__ == "__main__":
    app()
