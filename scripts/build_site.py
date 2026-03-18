#!/usr/bin/env python3
"""Build static GitHub Pages site from domain YAMLs."""

from __future__ import annotations

import json
from pathlib import Path

from robotics_paper_genealogy.graph.builder import build_graph, build_graph_from_domains
from robotics_paper_genealogy.models import Domain, RelationType, load_all_domains

RELATION_COLORS = {
    RelationType.extends: "#22c55e",
    RelationType.combines: "#06b6d4",
    RelationType.replaces: "#ef4444",
    RelationType.inspires: "#eab308",
}

RELATION_DASHES = {
    RelationType.extends: False,
    RelationType.combines: False,
    RelationType.replaces: False,
    RelationType.inspires: True,
}

DOMAINS_DIR = Path(__file__).parent.parent / "domains"
OUTPUT_DIR = Path(__file__).parent.parent / "docs"

CATEGORY_MAP = {
    "Perception (LiDAR)": [
        "LiDAR Odometry & SLAM",
        "Point Cloud Denoising",
        "Point Cloud Scene Flow",
        "3D Object Detection",
        "Visual Place Recognition",
    ],
    "Perception (Visual)": [
        "Neural Radiance Fields & 3D Gaussian Splatting",
        "Image Matching & Feature Detection",
        "Visual SLAM",
        "Depth Completion",
    ],
    "Planning & Control": [
        "Motion Planning",
        "Robot Control",
        "End-to-End Autonomous Driving",
    ],
    "Robot Learning": [
        "Imitation Learning & Robot Foundation Models",
        "World Models for Robotics & Embodied AI",
        "Legged Robot Control",
    ],
    "Foundation Models": [
        "Large Language Models",
        "Vision-Language Models",
    ],
    "Platforms & Simulation": [
        "Robot Simulation",
        "Medical & Surgical Robotics",
    ],
}


def domain_to_graph_data(domains: list[Domain]) -> dict:
    """Convert domains to vis.js compatible nodes and edges."""
    graph = build_graph_from_domains(domains)

    years = sorted({n.method.year for n in graph.nodes.values()})
    year_to_level = {y: i for i, y in enumerate(years)}

    nodes = []
    edges = []

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

        color = "#f97316" if not node.parent_nodes else "#3b82f6"

        nodes.append({
            "id": name,
            "label": f"{m.name}\n[{m.year}]",
            "title": title,
            "size": size,
            "color": color,
            "font": {"size": 18, "color": "white"},
            "level": year_to_level[m.year],
        })

    for name, node in graph.nodes.items():
        for parent_ref in node.method.parents:
            if parent_ref.name in graph.nodes:
                edges.append({
                    "from": parent_ref.name,
                    "to": name,
                    "color": RELATION_COLORS[parent_ref.relation],
                    "title": parent_ref.relation.value,
                    "dashes": RELATION_DASHES[parent_ref.relation],
                    "arrows": "to",
                    "width": 3,
                })

    return {"nodes": nodes, "edges": edges}


def build_site_data(domains: list[Domain]) -> dict:
    """Build all graph data for the site."""
    domain_by_name = {d.name: d for d in domains}

    site_data = {"categories": {}, "domains": {}}

    for cat_name, domain_names in CATEGORY_MAP.items():
        cat_domains = [domain_by_name[n] for n in domain_names if n in domain_by_name]
        site_data["categories"][cat_name] = {
            "domain_names": [d.name for d in cat_domains],
            "graph": domain_to_graph_data(cat_domains),
        }

    for d in domains:
        site_data["domains"][d.name] = {
            "description": d.description or "",
            "methods_count": len(d.methods),
            "graph": domain_to_graph_data([d]),
        }

    return site_data


INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Robotics Paper Genealogy</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0e1117; color: #ccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .header { padding: 16px 24px; border-bottom: 1px solid #333; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .header h1 { color: #fff; font-size: 20px; white-space: nowrap; }
  .header a { color: #888; text-decoration: none; font-size: 13px; }
  .header a:hover { color: #fff; }
  .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  select { background: #1a1d23; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; font-size: 14px; cursor: pointer; }
  select:hover { border-color: #666; }
  .stats { color: #888; font-size: 13px; white-space: nowrap; }
  #graph { width: 100%; height: calc(100vh - 70px); }
  .legend {
    position: fixed; top: 80px; right: 16px; z-index: 9999;
    background: rgba(14,17,23,0.9); border: 1px solid #333; border-radius: 8px;
    padding: 10px 14px; font-size: 13px; line-height: 1.7; pointer-events: none;
  }
  .legend b { color: #fff; }
</style>
</head>
<body>

<div class="header">
  <h1>Robotics Paper Genealogy</h1>
  <div class="controls">
    <select id="category"></select>
    <select id="domain"></select>
    <span class="stats" id="stats"></span>
  </div>
  <a href="https://github.com/rsasaki0109/robotics-paper-genealogy" target="_blank">GitHub</a>
</div>

<div id="graph"></div>

<div class="legend">
  <b>Edges</b><br>
  <span style="color:#22c55e">━━▶</span> extends<br>
  <span style="color:#06b6d4">━━▶</span> combines<br>
  <span style="color:#ef4444">━━▶</span> replaces<br>
  <span style="color:#eab308">╌╌▶</span> inspires<br>
  <b style="margin-top:4px;display:inline-block">Nodes</b><br>
  <span style="color:#f97316">●</span> Root &nbsp;
  <span style="color:#3b82f6">●</span> Derived
</div>

<script>
let DATA;
let network;

const OPTIONS = {
  layout: {
    hierarchical: {
      enabled: true,
      direction: "LR",
      sortMethod: "directed",
      levelSeparation: 300,
      nodeSpacing: 150
    }
  },
  physics: { enabled: false },
  edges: { smooth: { type: "cubicBezier" } },
  interaction: { hover: true, tooltipDelay: 100 }
};

function renderGraph(graphData) {
  const container = document.getElementById("graph");
  const data = {
    nodes: new vis.DataSet(graphData.nodes),
    edges: new vis.DataSet(graphData.edges)
  };
  if (network) network.destroy();
  network = new vis.Network(container, data, OPTIONS);
  document.getElementById("stats").textContent =
    graphData.nodes.length + " methods / " +
    graphData.edges.length + " edges";
}

function populateDomains(catName) {
  const domainSelect = document.getElementById("domain");
  domainSelect.innerHTML = "";

  const allOpt = document.createElement("option");
  allOpt.value = "__category__";
  allOpt.textContent = "All (" + DATA.categories[catName].domain_names.length + " domains)";
  domainSelect.appendChild(allOpt);

  for (const dName of DATA.categories[catName].domain_names) {
    const opt = document.createElement("option");
    opt.value = dName;
    const info = DATA.domains[dName];
    opt.textContent = dName + " (" + info.methods_count + ")";
    domainSelect.appendChild(opt);
  }
}

function onCategoryChange() {
  const catName = document.getElementById("category").value;
  populateDomains(catName);
  renderGraph(DATA.categories[catName].graph);
}

function onDomainChange() {
  const catName = document.getElementById("category").value;
  const domainName = document.getElementById("domain").value;
  if (domainName === "__category__") {
    renderGraph(DATA.categories[catName].graph);
  } else {
    renderGraph(DATA.domains[domainName].graph);
  }
}

fetch("data.json")
  .then(r => r.json())
  .then(d => {
    DATA = d;
    const catSelect = document.getElementById("category");
    for (const catName of Object.keys(DATA.categories)) {
      const opt = document.createElement("option");
      opt.value = catName;
      opt.textContent = catName;
      catSelect.appendChild(opt);
    }
    catSelect.addEventListener("change", onCategoryChange);
    document.getElementById("domain").addEventListener("change", onDomainChange);
    onCategoryChange();
  });
</script>
</body>
</html>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Loading domains...")
    domains = load_all_domains(DOMAINS_DIR)
    print(f"  {len(domains)} domains, {sum(len(d.methods) for d in domains)} methods")

    print("Building site data...")
    site_data = build_site_data(domains)

    data_path = OUTPUT_DIR / "data.json"
    with data_path.open("w") as f:
        json.dump(site_data, f, separators=(",", ":"))
    print(f"  data.json: {data_path.stat().st_size / 1024:.0f} KB")

    index_path = OUTPUT_DIR / "index.html"
    index_path.write_text(INDEX_HTML)
    print(f"  index.html written")

    print(f"\nDone! Open {OUTPUT_DIR}/index.html or deploy docs/ to GitHub Pages.")


if __name__ == "__main__":
    main()
