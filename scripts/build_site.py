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
            "Optical Flow",
            "Object Tracking",
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
            "Reinforcement Learning",
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
            "font": {"size": 30, "color": "white"},
            "level": year_to_level[m.year],
            "oss": oss.value,
            "hasPaper": m.has_paper,
            "year": m.year,
            "arxiv": m.arxiv or "",
            "code": m.code or "",
            "stars": m.stars or 0,
            "licenseName": m.license or "",
            "description": m.description or "",
            "tags": m.tags or [],
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
<meta property="og:title" content="Robotics Technology Genealogy">
<meta property="og:description" content="Interactive genealogy tree of 800+ Robotics & AI technologies across 28 domains">
<meta property="og:image" content="https://rsasaki0109.github.io/robotics-technology-genealogy/screenshot.png">
<meta property="og:url" content="https://rsasaki0109.github.io/robotics-technology-genealogy/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Robotics Technology Genealogy">
<meta name="twitter:description" content="Interactive genealogy tree of 800+ Robotics & AI technologies across 28 domains">
<meta name="twitter:image" content="https://rsasaki0109.github.io/robotics-technology-genealogy/screenshot.png">
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
  #info-panel {
    display: none; position: fixed; bottom: 0; left: 0; right: 0; z-index: 10000;
    background: #161b22; border-top: 1px solid #333; padding: 16px 24px;
    font-size: 14px; color: #ccc; max-height: 220px; overflow-y: auto;
  }
  #info-panel.visible { display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }
  #info-panel .info-main { flex: 1; min-width: 280px; }
  #info-panel h2 { color: #fff; font-size: 18px; margin-bottom: 6px; }
  #info-panel .info-year { color: #888; font-size: 14px; margin-bottom: 8px; }
  #info-panel .info-desc { color: #aaa; margin-bottom: 8px; line-height: 1.5; }
  #info-panel .info-links { display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
  #info-panel .info-links a { color: #58a6ff; text-decoration: none; font-size: 13px; }
  #info-panel .info-links a:hover { text-decoration: underline; }
  #info-panel .info-meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 13px; color: #888; }
  #info-panel .tag { display: inline-block; background: #21262d; border: 1px solid #333; border-radius: 12px; padding: 2px 10px; font-size: 12px; color: #8b949e; margin: 2px 2px; }
  #info-panel .close-btn {
    position: absolute; top: 10px; right: 16px; background: none; border: none;
    color: #888; font-size: 20px; cursor: pointer; line-height: 1;
  }
  #info-panel .close-btn:hover { color: #fff; }
  .legend {
    position: fixed; top: 80px; right: 16px; z-index: 9999;
    background: rgba(14,17,23,0.9); border: 1px solid #333; border-radius: 8px;
    padding: 10px 14px; font-size: 13px; line-height: 1.7; pointer-events: none;
  }
  .legend b { color: #fff; }
  #stats-overlay {
    display: none; position: fixed; inset: 0; z-index: 20000;
    background: rgba(0,0,0,0.7); justify-content: center; align-items: center;
  }
  #stats-overlay.visible { display: flex; }
  .stats-panel {
    background: #161b22; border: 1px solid #333; border-radius: 12px;
    padding: 28px 32px; max-width: 720px; width: 90%; max-height: 85vh;
    overflow-y: auto; color: #ccc; font-size: 14px; position: relative;
  }
  .stats-panel h2 { color: #fff; font-size: 22px; margin-bottom: 20px; }
  .stats-panel h3 { color: #ddd; font-size: 15px; margin: 18px 0 8px; }
  .stats-panel .close-btn {
    position: absolute; top: 12px; right: 16px; background: none; border: none;
    color: #888; font-size: 22px; cursor: pointer;
  }
  .stats-panel .close-btn:hover { color: #fff; }
  .stats-big { display: flex; gap: 40px; margin-bottom: 12px; }
  .stats-big .num { font-size: 42px; font-weight: 700; color: #3b82f6; }
  .stats-big .label { font-size: 13px; color: #888; }
  .bar-row { display: flex; align-items: center; gap: 8px; margin: 2px 0; font-size: 12px; font-family: monospace; }
  .bar-row .bar-label { width: 40px; text-align: right; color: #888; }
  .bar-row .bar { background: #3b82f6; height: 14px; border-radius: 2px; min-width: 2px; }
  .bar-row .bar-count { color: #888; width: 30px; }
  .oss-row { display: flex; align-items: center; gap: 8px; margin: 3px 0; font-size: 13px; }
  .oss-row .oss-bar { height: 16px; border-radius: 3px; }
  .star-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; border-bottom: 1px solid #222; }
  .star-row a { color: #58a6ff; text-decoration: none; }
  .star-row a:hover { text-decoration: underline; }
  .star-row .star-count { color: #eab308; white-space: nowrap; }
  @media (max-width: 768px) {
    .header { flex-direction: column; align-items: flex-start; padding: 12px 16px; }
    .header h1 { font-size: 16px; }
    .controls { flex-wrap: wrap; gap: 8px; }
    select, #search { font-size: 12px; padding: 6px 8px; width: 100%; }
    .filter-btn { font-size: 11px; padding: 4px 8px; }
    #graph { height: calc(100vh - 120px); }
    .legend { font-size: 11px; padding: 6px 10px; top: auto; bottom: 12px; right: 12px; }
    #info-panel { font-size: 13px; }
    #stats-overlay { width: 95%; left: 2.5%; }
  }
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
    <button class="filter-btn" id="btn-stats" title="Show project statistics">Stats</button>
    <span class="stats" id="stats"></span>
  </div>
  <a href="https://github.com/rsasaki0109/robotics-technology-genealogy" target="_blank">GitHub</a>
</div>

<div id="graph"></div>

<div id="info-panel">
  <button class="close-btn" onclick="closeInfoPanel()">&times;</button>
  <div class="info-main">
    <h2 id="info-name"></h2>
    <div class="info-year" id="info-year"></div>
    <div class="info-desc" id="info-desc"></div>
    <div class="info-links" id="info-links"></div>
    <div class="info-meta" id="info-meta"></div>
    <div id="info-tags" style="margin-top:6px"></div>
  </div>
</div>

<div id="stats-overlay">
  <div class="stats-panel">
    <button class="close-btn" onclick="toggleStatsPanel()">&times;</button>
    <h2>Project Statistics</h2>
    <div class="stats-big">
      <div><div class="num" id="st-methods">-</div><div class="label">Methods</div></div>
      <div><div class="num" id="st-domains">-</div><div class="label">Domains</div></div>
    </div>
    <h3>Methods per Year</h3>
    <div id="st-year-chart"></div>
    <h3>Open Source Breakdown</h3>
    <div id="st-oss"></div>
    <h3>Top 10 Repos by Stars</h3>
    <div id="st-top-stars"></div>
  </div>
</div>

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
  network.on("click", function(params) {
    if (params.nodes.length === 1) {
      const nodeId = params.nodes[0];
      const nodeData = data.nodes.get(nodeId);
      if (nodeData) showInfoPanel(nodeData);
    } else {
      closeInfoPanel();
    }
  });
  const total = graphData.nodes.length;
  const shown = filtered.nodes.length;
  const statsText = shown < total
    ? shown + "/" + total + " methods (filtered) / " + filtered.edges.length + " edges"
    : total + " methods / " + filtered.edges.length + " edges";
  document.getElementById("stats").textContent = statsText;
}

function closeInfoPanel() {
  document.getElementById("info-panel").classList.remove("visible");
}

function showInfoPanel(nodeData) {
  const panel = document.getElementById("info-panel");
  document.getElementById("info-name").textContent = nodeData.label.replace(/\\n/g, " ");
  document.getElementById("info-year").textContent = "Year: " + (nodeData.year || "N/A");
  document.getElementById("info-desc").textContent = nodeData.description || "";

  const linksEl = document.getElementById("info-links");
  linksEl.innerHTML = "";
  if (nodeData.arxiv) {
    const a = document.createElement("a");
    a.href = "https://arxiv.org/abs/" + nodeData.arxiv;
    a.target = "_blank";
    a.textContent = "arXiv: " + nodeData.arxiv;
    linksEl.appendChild(a);
  }
  if (nodeData.code) {
    const a = document.createElement("a");
    a.href = "https://github.com/" + nodeData.code;
    a.target = "_blank";
    a.textContent = "GitHub: " + nodeData.code;
    linksEl.appendChild(a);
  }

  const metaEl = document.getElementById("info-meta");
  metaEl.innerHTML = "";
  if (nodeData.stars) { metaEl.innerHTML += "<span>★ " + nodeData.stars.toLocaleString() + "</span>"; }
  if (nodeData.oss && nodeData.oss !== "unknown") { metaEl.innerHTML += "<span>OSS: " + nodeData.oss + "</span>"; }
  if (nodeData.licenseName) { metaEl.innerHTML += "<span>License: " + nodeData.licenseName + "</span>"; }

  const tagsEl = document.getElementById("info-tags");
  tagsEl.innerHTML = "";
  if (nodeData.tags && nodeData.tags.length) {
    nodeData.tags.forEach(function(t) {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = t;
      tagsEl.appendChild(span);
    });
  }

  panel.classList.add("visible");
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

let STATS = null;

function toggleStatsPanel() {
  const overlay = document.getElementById("stats-overlay");
  const btn = document.getElementById("btn-stats");
  const isVisible = overlay.classList.toggle("visible");
  btn.classList.toggle("active", isVisible);
}

function renderStatsPanel(stats) {
  document.getElementById("st-methods").textContent = stats.total_methods;
  document.getElementById("st-domains").textContent = stats.total_domains;

  // Year histogram
  const yearDiv = document.getElementById("st-year-chart");
  yearDiv.innerHTML = "";
  const maxCount = Math.max(...stats.methods_per_year.map(d => d.count));
  const barMaxWidth = 320;
  stats.methods_per_year.forEach(d => {
    const w = Math.round((d.count / maxCount) * barMaxWidth);
    yearDiv.innerHTML += '<div class="bar-row"><span class="bar-label">' + d.year +
      '</span><div class="bar" style="width:' + w + 'px"></div><span class="bar-count">' +
      d.count + '</span></div>';
  });

  // OSS breakdown
  const ossDiv = document.getElementById("st-oss");
  ossDiv.innerHTML = "";
  const ossColors = { open: "#22c55e", research: "#eab308", partial: "#f97316", closed: "#ef4444", unknown: "#555" };
  const ossTotal = Object.values(stats.oss_breakdown).reduce((a, b) => a + b, 0);
  // Stacked bar
  let stackedHtml = '<div style="display:flex;border-radius:4px;overflow:hidden;height:22px;margin-bottom:8px">';
  for (const [key, count] of Object.entries(stats.oss_breakdown)) {
    if (count === 0) continue;
    const pct = (count / ossTotal * 100).toFixed(1);
    stackedHtml += '<div style="width:' + pct + '%;background:' + ossColors[key] + '" title="' + key + ': ' + count + '"></div>';
  }
  stackedHtml += '</div>';
  ossDiv.innerHTML = stackedHtml;
  for (const [key, count] of Object.entries(stats.oss_breakdown)) {
    const pct = (count / ossTotal * 100).toFixed(1);
    ossDiv.innerHTML += '<div class="oss-row"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:' +
      ossColors[key] + '"></span> ' + key + ': ' + count + ' (' + pct + '%)</div>';
  }

  // Top 10 stars
  const starsDiv = document.getElementById("st-top-stars");
  starsDiv.innerHTML = "";
  stats.top_by_stars.slice(0, 10).forEach(m => {
    const link = m.code ? '<a href="https://github.com/' + m.code + '" target="_blank">' + m.name + '</a>' : m.name;
    starsDiv.innerHTML += '<div class="star-row"><span>' + link + ' <span style="color:#888">(' + m.year +
      ')</span></span><span class="star-count">★ ' + m.stars.toLocaleString() + '</span></div>';
  });
}

fetch("stats.json").then(r => r.json()).then(s => { STATS = s; renderStatsPanel(s); }).catch(() => {});

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
    document.getElementById("btn-stats").addEventListener("click", () => toggleStatsPanel());
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

    print("Building stats...")
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from build_stats import generate_stats_json
    stats_path = generate_stats_json(domains, OUTPUT_DIR)
    print(f"  stats.json: {stats_path.stat().st_size / 1024:.1f} KB")

    index_path = OUTPUT_DIR / "index.html"
    index_path.write_text(INDEX_HTML)
    print(f"  index.html written")

    print(f"\nDone! Open {OUTPUT_DIR}/index.html or deploy docs/ to GitHub Pages.")


if __name__ == "__main__":
    main()
