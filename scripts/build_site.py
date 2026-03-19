#!/usr/bin/env python3
"""Build static GitHub Pages site from domain YAMLs."""

from __future__ import annotations

import json
from pathlib import Path

from robotics_technology_genealogy.graph.builder import build_graph, build_graph_from_domains
from robotics_technology_genealogy.models import Domain, OpenSourceStatus, RelationType, load_all_domains

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
    "Perception (LiDAR/3D)": [
        "LiDAR Odometry & SLAM",
        "3D Object Detection",
        "Point Cloud Denoising",
        "Point Cloud Scene Flow",
        "Place Recognition",
    ],
    "Perception (Visual)": [
        "Neural Radiance Fields & 3D Gaussian Splatting",
        "Image Matching & Feature Detection",
        "Visual SLAM",
        "Depth Completion",
        "2D Object Detection",
        "Semantic Segmentation",
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
        "Grasp Planning & Manipulation",
    ],
    "Foundation Models": [
        "Large Language Models",
        "Vision-Language Models",
        "Diffusion Models",
            "Vision Backbone & Foundation",
    ],
    "Platforms & Simulation": [
        "Robot Simulation",
        "Robot Middleware & Frameworks",
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

        oss = m.inferred_open_source
        oss_str = f"\n🔓 {oss.value}" if oss != OpenSourceStatus.unknown else ""
        license_str = f"\n📜 {m.license}" if m.license else ""
        stars_str = f"\n★ {m.stars:,}" if m.stars else ""
        code_str = f"\n📦 github.com/{m.code}" if m.code else ""
        arxiv_str = f"\n📄 arxiv.org/abs/{m.arxiv}" if m.arxiv else ""
        paper_str = "" if m.has_paper else "\n⚠️ No paper (code/product only)"
        tags_str = f"\nTags: {', '.join(m.tags)}" if m.tags else ""
        desc_str = f"\n{m.description}" if m.description else ""

        title = f"{m.name} [{m.year}]{oss_str}{license_str}{stars_str}{desc_str}{code_str}{arxiv_str}{paper_str}{tags_str}"

        # Base color by root/derived
        base_color = "#f97316" if not node.parent_nodes else "#3b82f6"

        # Border indicates open source status
        BORDER_COLORS = {
            OpenSourceStatus.open: "#22c55e",      # green
            OpenSourceStatus.research: "#eab308",   # yellow
            OpenSourceStatus.partial: "#f97316",    # orange
            OpenSourceStatus.closed: "#ef4444",     # red
            OpenSourceStatus.unknown: "#555555",    # gray
        }
        border_color = BORDER_COLORS[oss]

        nodes.append({
            "id": name,
            "label": f"{m.name}\n[{m.year}]",
            "title": title,
            "size": size,
            "color": {
                "background": base_color,
                "border": border_color,
                "highlight": {"background": base_color, "border": "#ffffff"},
            },
            "borderWidth": 3,
            "font": {"size": 24, "color": "white"},
            "level": year_to_level[m.year],
            "oss": oss.value,
            "hasPaper": m.has_paper,
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

    site_data = {"categories": {}, "domains": {}, "method_index": {}}

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

    # Build method -> domain reverse index
    for d in domains:
        for m in d.methods:
            if m.name not in site_data["method_index"]:
                site_data["method_index"][m.name] = d.name

    return site_data


INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Robotics Technology Genealogy</title>
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
  #search { background: #1a1d23; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; font-size: 14px; width: 200px; }
  #search:focus { border-color: #3b82f6; outline: none; }
  .filter-btn { background: #1a1d23; color: #888; border: 1px solid #444; border-radius: 6px; padding: 6px 10px; font-size: 12px; cursor: pointer; }
  .filter-btn.active { color: #fff; border-color: #22c55e; background: #1a2e1a; }
  .filter-btn:hover { border-color: #666; }
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
  <h1>Robotics Technology Genealogy</h1>
  <div class="controls">
    <select id="category"></select>
    <select id="domain"></select>
    <input type="text" id="search" placeholder="Search method..." autocomplete="off" list="search-list">
    <datalist id="search-list"></datalist>
    <button class="filter-btn" id="btn-oss" title="Show only open source">OSS Only</button>
    <button class="filter-btn" id="btn-paper" title="Show only with paper">Paper Only</button>
    <button class="filter-btn" id="btn-nopaper" title="Show only without paper">No Paper</button>
    <span class="stats" id="stats"></span>
  </div>
  <a href="https://github.com/rsasaki0109/robotics-technology-genealogy" target="_blank">GitHub</a>
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
  <span style="color:#3b82f6">●</span> Derived<br>
  <b style="margin-top:4px;display:inline-block">Border (OSS)</b><br>
  <span style="color:#22c55e">◉</span> Open source<br>
  <span style="color:#eab308">◉</span> Research only<br>
  <span style="color:#f97316">◉</span> Partial<br>
  <span style="color:#ef4444">◉</span> Closed<br>
  <span style="color:#555">◉</span> Unknown
</div>

<script>
let DATA;
let network;
let currentGraphData = null;
let filters = { oss: false, paper: false, nopaper: false };

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

function applyFilters(graphData) {
  let nodes = graphData.nodes;
  if (filters.oss) {
    nodes = nodes.filter(n => n.oss === "open");
  }
  if (filters.paper) {
    nodes = nodes.filter(n => n.hasPaper === true);
  }
  if (filters.nopaper) {
    nodes = nodes.filter(n => n.hasPaper === false);
  }
  const nodeIds = new Set(nodes.map(n => n.id));
  const edges = graphData.edges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
  return { nodes, edges };
}

function renderGraph(graphData, save) {
  if (save !== false) currentGraphData = graphData;
  const filtered = applyFilters(graphData);
  const container = document.getElementById("graph");
  const data = {
    nodes: new vis.DataSet(filtered.nodes),
    edges: new vis.DataSet(filtered.edges)
  };
  if (network) network.destroy();
  network = new vis.Network(container, data, OPTIONS);
  const total = graphData.nodes.length;
  const shown = filtered.nodes.length;
  const statsText = shown < total
    ? shown + "/" + total + " methods (filtered) / " + filtered.edges.length + " edges"
    : total + " methods / " + filtered.edges.length + " edges";
  document.getElementById("stats").textContent = statsText;
}

function toggleFilter(key, btnId) {
  filters[key] = !filters[key];
  // nopaper and paper are mutually exclusive
  if (key === "paper" && filters.paper) filters.nopaper = false;
  if (key === "nopaper" && filters.nopaper) filters.paper = false;
  document.getElementById("btn-oss").classList.toggle("active", filters.oss);
  document.getElementById("btn-paper").classList.toggle("active", filters.paper);
  document.getElementById("btn-nopaper").classList.toggle("active", filters.nopaper);
  if (currentGraphData) renderGraph(currentGraphData, false);
}

function buildSearchIndex() {
  const list = document.getElementById("search-list");
  for (const name of Object.keys(DATA.method_index)) {
    const opt = document.createElement("option");
    opt.value = name;
    list.appendChild(opt);
  }
}

function searchMethod(query) {
  if (!query || !DATA.method_index[query]) return;
  const domainName = DATA.method_index[query];

  // Find which category contains this domain
  for (const [catName, catData] of Object.entries(DATA.categories)) {
    if (catData.domain_names.includes(domainName)) {
      // Switch category
      document.getElementById("category").value = catName;
      populateDomains(catName);
      // Switch domain
      document.getElementById("domain").value = domainName;
      renderGraph(DATA.domains[domainName].graph);
      // Focus on the node after a short delay
      setTimeout(() => {
        if (network) {
          network.selectNodes([query]);
          network.focus(query, { scale: 1.2, animation: { duration: 500 } });
        }
      }, 300);
      break;
    }
  }
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
    document.getElementById("btn-oss").addEventListener("click", () => toggleFilter("oss"));
    document.getElementById("btn-paper").addEventListener("click", () => toggleFilter("paper"));
    document.getElementById("btn-nopaper").addEventListener("click", () => toggleFilter("nopaper"));
    const searchInput = document.getElementById("search");
    searchInput.addEventListener("change", (e) => { searchMethod(e.target.value); e.target.value = ""; });
    searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { searchMethod(e.target.value); e.target.value = ""; } });
    buildSearchIndex();
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
