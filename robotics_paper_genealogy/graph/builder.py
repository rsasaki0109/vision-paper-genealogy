"""Build genealogy graph from domain data."""

from __future__ import annotations

from dataclasses import dataclass, field

from robotics_paper_genealogy.models import Domain, Method, RelationType


@dataclass
class MethodNode:
    method: Method
    children: list[tuple[MethodNode, RelationType]] = field(default_factory=list)
    parent_nodes: list[tuple[MethodNode, RelationType]] = field(default_factory=list)


class GenealogyGraph:
    """Genealogy graph of research methods."""

    def __init__(self) -> None:
        self.nodes: dict[str, MethodNode] = {}

    def add_method(self, method: Method) -> MethodNode:
        node = MethodNode(method=method)
        self.nodes[method.name] = node
        return node

    def build_edges(self) -> None:
        """Build parent-child edges after all methods are added."""
        for node in self.nodes.values():
            for parent_ref in node.method.parents:
                parent_node = self.nodes.get(parent_ref.name)
                if parent_node is not None:
                    parent_node.children.append((node, parent_ref.relation))
                    node.parent_nodes.append((parent_node, parent_ref.relation))

    def get_roots(self) -> list[MethodNode]:
        """Get methods with no parents (root of the genealogy)."""
        return [n for n in self.nodes.values() if not n.parent_nodes]

    def get_ancestors(self, name: str) -> list[tuple[MethodNode, RelationType, int]]:
        """Get all ancestors of a method with their depth."""
        node = self.nodes.get(name)
        if node is None:
            return []
        ancestors: list[tuple[MethodNode, RelationType, int]] = []
        visited: set[str] = set()
        self._collect_ancestors(node, ancestors, visited, 0)
        return ancestors

    def _collect_ancestors(
        self,
        node: MethodNode,
        ancestors: list[tuple[MethodNode, RelationType, int]],
        visited: set[str],
        depth: int,
    ) -> None:
        for parent_node, relation in node.parent_nodes:
            if parent_node.method.name not in visited:
                visited.add(parent_node.method.name)
                ancestors.append((parent_node, relation, depth + 1))
                self._collect_ancestors(parent_node, ancestors, visited, depth + 1)

    def get_descendants(self, name: str) -> list[tuple[MethodNode, RelationType, int]]:
        """Get all descendants of a method with their depth."""
        node = self.nodes.get(name)
        if node is None:
            return []
        descendants: list[tuple[MethodNode, RelationType, int]] = []
        visited: set[str] = set()
        self._collect_descendants(node, descendants, visited, 0)
        return descendants

    def _collect_descendants(
        self,
        node: MethodNode,
        descendants: list[tuple[MethodNode, RelationType, int]],
        visited: set[str],
        depth: int,
    ) -> None:
        for child_node, relation in node.children:
            if child_node.method.name not in visited:
                visited.add(child_node.method.name)
                descendants.append((child_node, relation, depth + 1))
                self._collect_descendants(child_node, descendants, visited, depth + 1)


def build_graph(domain: Domain) -> GenealogyGraph:
    """Build a genealogy graph from a domain."""
    graph = GenealogyGraph()
    for method in domain.methods:
        graph.add_method(method)
    graph.build_edges()
    return graph


def build_graph_from_domains(domains: list[Domain]) -> GenealogyGraph:
    """Build a unified genealogy graph from multiple domains."""
    graph = GenealogyGraph()
    for domain in domains:
        for method in domain.methods:
            if method.name not in graph.nodes:
                graph.add_method(method)
    graph.build_edges()
    return graph
