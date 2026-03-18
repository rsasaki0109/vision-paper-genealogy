"""Web visualization using pyvis."""

from __future__ import annotations

from pathlib import Path

from pyvis.network import Network

from robotics_technology_genealogy.graph.builder import GenealogyGraph
from robotics_technology_genealogy.models import RelationType

RELATION_COLORS = {
    RelationType.extends: "#22c55e",   # green
    RelationType.combines: "#06b6d4",  # cyan
    RelationType.replaces: "#ef4444",  # red
    RelationType.inspires: "#eab308",  # yellow
}

RELATION_DASHES = {
    RelationType.extends: False,
    RelationType.combines: False,
    RelationType.replaces: False,
    RelationType.inspires: True,  # dashed line for indirect influence
}


def build_pyvis_network(graph: GenealogyGraph, height: str = "700px") -> Network:
    """Build a pyvis Network from a GenealogyGraph."""
    net = Network(
        height=height,
        width="100%",
        directed=True,
        bgcolor="#0e1117",
        font_color="white",
        notebook=False,
    )
    # Hierarchical layout: left-to-right by year
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 300,
          "nodeSpacing": 150
        }
      },
      "physics": {
        "enabled": false
      }
    }
    """)

    # Assign level based on year for chronological ordering
    years = sorted({n.method.year for n in graph.nodes.values()})
    year_to_level = {y: i for i, y in enumerate(years)}

    for name, node in graph.nodes.items():
        m = node.method
        size = 25
        if m.stars:
            if m.stars > 10000:
                size = 55
            elif m.stars > 5000:
                size = 42
            elif m.stars > 1000:
                size = 32

        stars_str = f"\n★ {m.stars:,}" if m.stars else ""
        code_str = f"\n📦 github.com/{m.code}" if m.code else ""
        arxiv_str = f"\n📄 arxiv.org/abs/{m.arxiv}" if m.arxiv else ""
        tags_str = f"\nTags: {', '.join(m.tags)}" if m.tags else ""
        desc_str = f"\n{m.description}" if m.description else ""

        title = f"{m.name} [{m.year}]{stars_str}{desc_str}{code_str}{arxiv_str}{tags_str}"

        color = "#3b82f6"  # default blue
        if not node.parent_nodes:
            color = "#f97316"  # orange for roots

        net.add_node(
            name,
            label=f"{m.name}\n[{m.year}]",
            title=title,
            size=size,
            color=color,
            font={"size": 18, "color": "white"},
            level=year_to_level[m.year],
        )

    for name, node in graph.nodes.items():
        for parent_ref in node.method.parents:
            if parent_ref.name in graph.nodes:
                edge_color = RELATION_COLORS[parent_ref.relation]
                dashes = RELATION_DASHES[parent_ref.relation]
                net.add_edge(
                    parent_ref.name,
                    name,
                    color=edge_color,
                    title=parent_ref.relation.value,
                    dashes=dashes,
                    arrows="to",
                    width=3,
                )

    return net


LEGEND_HTML = """\
<div style="
    position: absolute; top: 12px; right: 12px; z-index: 9999;
    background: rgba(14,17,23,0.85); border: 1px solid #333; border-radius: 8px;
    padding: 10px 14px; font-family: sans-serif; font-size: 13px; color: #ccc;
    pointer-events: none; line-height: 1.7;
">
  <div style="font-weight:bold; color:#fff; margin-bottom:4px;">Edges</div>
  <span style="color:#22c55e">━━▶</span> extends<br>
  <span style="color:#06b6d4">━━▶</span> combines<br>
  <span style="color:#ef4444">━━▶</span> replaces<br>
  <span style="color:#eab308">╌╌▶</span> inspires<br>
  <div style="font-weight:bold; color:#fff; margin-top:6px; margin-bottom:4px;">Nodes</div>
  <span style="color:#f97316">●</span> Root &nbsp;
  <span style="color:#3b82f6">●</span> Derived
</div>
"""


def export_html(graph: GenealogyGraph, output_path: str | Path, height: str = "700px") -> Path:
    """Export the genealogy graph as an interactive HTML file."""
    output_path = Path(output_path)
    net = build_pyvis_network(graph, height=height)
    net.save_graph(str(output_path))

    # Inject legend overlay into the HTML
    html = output_path.read_text()
    html = html.replace("<body>", f"<body>\n{LEGEND_HTML}")
    output_path.write_text(html)

    return output_path
