"""Terminal tree visualization using rich."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from robotics_paper_genealogy.graph.builder import GenealogyGraph, MethodNode
from robotics_paper_genealogy.models import RelationType

RELATION_SYMBOLS = {
    RelationType.extends: "\u2191",    # ↑
    RelationType.combines: "\u002b",   # +
    RelationType.replaces: "\u21e8",   # ⇨
    RelationType.inspires: "\u2731",   # ✱
}

RELATION_COLORS = {
    RelationType.extends: "green",
    RelationType.combines: "cyan",
    RelationType.replaces: "red",
    RelationType.inspires: "yellow",
}


def _format_method(node: MethodNode, relation: RelationType | None = None) -> Text:
    """Format a method node for display."""
    m = node.method
    text = Text()

    if relation is not None:
        color = RELATION_COLORS[relation]
        symbol = RELATION_SYMBOLS[relation]
        text.append(f"({symbol} {relation.value}) ", style=color)

    text.append(m.name, style="bold white")
    text.append(f" [{m.year}]", style="dim")

    if m.stars is not None:
        text.append(f" \u2605{m.stars:,}", style="yellow")

    if m.code:
        text.append(f" \U0001f4e6", style="dim")  # 📦

    if m.arxiv:
        text.append(f" \U0001f4c4", style="dim")  # 📄

    return text


def _add_children(tree: Tree, node: MethodNode, visited: set[str]) -> None:
    """Recursively add children to the tree."""
    for child_node, relation in sorted(node.children, key=lambda x: x[0].method.year):
        if child_node.method.name in visited:
            tree.add(Text(f"... {child_node.method.name} (see above)", style="dim"))
            continue
        visited.add(child_node.method.name)
        label = _format_method(child_node, relation)
        branch = tree.add(label)
        _add_children(branch, child_node, visited)


def render_tree(graph: GenealogyGraph, console: Console | None = None) -> None:
    """Render the full genealogy tree to the terminal."""
    if console is None:
        console = Console()

    roots = graph.get_roots()
    if not roots:
        console.print("[dim]No methods found.[/dim]")
        return

    roots.sort(key=lambda n: n.method.year)
    visited: set[str] = set()

    for root in roots:
        if root.method.name in visited:
            continue
        visited.add(root.method.name)
        label = _format_method(root)
        tree = Tree(label)
        _add_children(tree, root, visited)
        console.print(tree)
        console.print()


def render_ancestors(graph: GenealogyGraph, method_name: str, console: Console | None = None) -> None:
    """Render the ancestor chain of a method."""
    if console is None:
        console = Console()

    node = graph.nodes.get(method_name)
    if node is None:
        console.print(f"[red]Method '{method_name}' not found.[/red]")
        return

    ancestors = graph.get_ancestors(method_name)
    if not ancestors:
        console.print(f"[dim]{method_name} has no known ancestors (it's a root method).[/dim]")
        return

    console.print(f"[bold]Ancestors of {method_name}:[/bold]\n")
    for ancestor_node, relation, depth in ancestors:
        indent = "  " * depth
        m = ancestor_node.method
        color = RELATION_COLORS[relation]
        symbol = RELATION_SYMBOLS[relation]
        console.print(
            f"{indent}{symbol} [bold]{m.name}[/bold] [{m.year}] "
            f"[{color}]({relation.value})[/{color}]"
        )


def render_method_detail(graph: GenealogyGraph, method_name: str, console: Console | None = None) -> None:
    """Render detailed info about a specific method."""
    if console is None:
        console = Console()

    node = graph.nodes.get(method_name)
    if node is None:
        console.print(f"[red]Method '{method_name}' not found.[/red]")
        return

    m = node.method
    console.print(f"\n[bold]{m.name}[/bold] [{m.year}]")
    if m.description:
        console.print(f"  {m.description}")
    if m.paper:
        console.print(f"  Paper: {m.paper}")
    if m.arxiv:
        console.print(f"  arXiv: https://arxiv.org/abs/{m.arxiv}")
    if m.code:
        console.print(f"  Code:  https://github.com/{m.code}")
    if m.stars is not None:
        console.print(f"  Stars: \u2605 {m.stars:,}")
    if m.tags:
        console.print(f"  Tags:  {', '.join(m.tags)}")

    if node.parent_nodes:
        console.print("\n  [bold]Parents:[/bold]")
        for parent, relation in node.parent_nodes:
            console.print(f"    {RELATION_SYMBOLS[relation]} {parent.method.name} ({relation.value})")

    if node.children:
        console.print("\n  [bold]Children:[/bold]")
        for child, relation in node.children:
            console.print(f"    {RELATION_SYMBOLS[relation]} {child.method.name} ({relation.value})")

    console.print()
