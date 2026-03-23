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

        rec_prefix = "\u2b50 " if m.recommended else ""
        if m.recommended:
            size = max(size, 40)

        nodes.append({
            "id": name,
            "label": f"{rec_prefix}{m.name}\n[{m.year}]",
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
            "recommended": m.recommended,
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
        methods = d.methods
        # Find highlights
        top_star = max(methods, key=lambda m: m.stars or 0)
        latest = max(methods, key=lambda m: m.year)
        roots = [m for m in methods if not m.parents]
        year_min = min(m.year for m in methods)
        year_max = max(m.year for m in methods)
        oss_count = sum(1 for m in methods if m.inferred_open_source.value == "open")

        site_data["domains"][d.name] = {
            "description": d.description or "",
            "methods_count": len(methods),
            "graph": domain_to_graph_data([d]),
            "highlights": {
                "top_star": {"name": top_star.name, "stars": top_star.stars or 0, "year": top_star.year},
                "latest": {"name": latest.name, "year": latest.year},
                "roots": [r.name for r in roots[:3]],
                "year_range": f"{year_min}–{year_max}",
                "oss_ratio": f"{oss_count}/{len(methods)}",
            },
        }

    # Build method -> domain reverse index
    for d in domains:
        for m in d.methods:
            if m.name not in site_data["method_index"]:
                site_data["method_index"][m.name] = d.name

    # Generate fun facts / insights
    all_methods = [m for d in domains for m in d.methods]
    facts = []

    total = len(all_methods)
    oldest = min(all_methods, key=lambda m: m.year)
    newest = max(all_methods, key=lambda m: m.year)
    facts.append(f"{total} technologies tracked — from {oldest.name} ({oldest.year}) to {newest.name} ({newest.year})")

    top_stars = sorted([m for m in all_methods if m.stars], key=lambda m: m.stars, reverse=True)
    if top_stars:
        t = top_stars[0]
        facts.append(f"Most starred: {t.name} with ★{t.stars:,} on GitHub")

    # Count children per method across all domains
    child_count: dict[str, int] = {}
    for d in domains:
        for m in d.methods:
            for p in m.parents:
                child_count[p.name] = child_count.get(p.name, 0) + 1
    if child_count:
        most_influential = max(child_count, key=child_count.get)
        facts.append(f"Most influential: {most_influential} → {child_count[most_influential]} direct descendants")

    oss_count = sum(1 for m in all_methods if m.inferred_open_source.value == "open")
    facts.append(f"Open source ratio: {oss_count}/{total} ({100*oss_count//total}%) methods have public code")

    # Count methods with children (influential)
    methods_with_children = sum(1 for v in child_count.values() if v >= 3)
    facts.append(f"{methods_with_children} methods spawned 3+ descendants — click any ⭐ node to start exploring")

    # Domain-specific highlights
    for d in domains:
        if len(d.methods) >= 30:
            top = max(d.methods, key=lambda m: m.stars or 0)
            if top.stars and top.stars > 5000:
                facts.append(f"{d.name}: {len(d.methods)} methods — led by {top.name} (★{top.stars:,})")

    site_data["facts"] = facts

    # Hot 2025: recent high-star methods
    recent = [m for m in all_methods if m.year >= 2024]
    recent.sort(key=lambda m: m.stars or 0, reverse=True)
    hot_2025 = []
    seen_names: set[str] = set()
    domain_count: dict[str, int] = {}
    MAX_PER_DOMAIN = 2
    for m in recent:
        if m.name in seen_names:
            continue
        domain_name = next((d.name for d in domains if m in d.methods), "")
        if domain_count.get(domain_name, 0) >= MAX_PER_DOMAIN:
            continue
        seen_names.add(m.name)
        domain_count[domain_name] = domain_count.get(domain_name, 0) + 1
        hot_2025.append({
            "name": m.name,
            "year": m.year,
            "stars": m.stars or 0,
            "domain": domain_name,
            "code": m.code or "",
            "arxiv": m.arxiv or "",
        })
        if len(hot_2025) >= 15:
            break
    site_data["hot_2025"] = hot_2025

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
  #stories {
    display: flex; gap: 0; border-bottom: 1px solid #333; overflow-x: auto;
    scrollbar-width: none;
  }
  #stories::-webkit-scrollbar { display: none; }
  .story-card {
    flex: 1; min-width: 180px; padding: 12px 16px; cursor: pointer;
    display: flex; gap: 10px; align-items: center;
    border-right: 1px solid #222; transition: background 0.2s;
  }
  .story-card:hover { background: #1a2e1a; }
  .story-card:last-child { border-right: none; }
  .story-icon { font-size: 24px; flex-shrink: 0; }
  .story-text { font-size: 12px; line-height: 1.4; color: #aaa; }
  .story-text b { color: #fff; font-size: 13px; }
  .next-link { color: #22c55e; cursor: pointer; text-decoration: underline; }
  .next-link:hover { color: #4ade80; }
  #domain-banner {
    display: none; padding: 10px 24px; background: #161b22; border-bottom: 1px solid #333;
    font-size: 13px; color: #aaa; gap: 24px; align-items: center; flex-wrap: wrap;
  }
  #domain-banner.visible { display: flex; }
  #domain-banner .desc { flex: 1; min-width: 200px; color: #ccc; }
  #domain-banner .chips { display: flex; gap: 8px; flex-wrap: wrap; }
  #domain-banner .chip {
    background: #1a1d23; border: 1px solid #444; border-radius: 12px;
    padding: 3px 10px; font-size: 12px; white-space: nowrap;
  }
  #domain-banner .chip b { color: #fff; }
  #domain-banner .chip.star { border-color: #eab308; color: #eab308; }
  #domain-banner .chip.latest { border-color: #22c55e; color: #22c55e; }
  #domain-banner .chip.oss { border-color: #3b82f6; color: #3b82f6; }
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
  #stats-overlay, #hot-overlay {
    display: none; position: fixed; inset: 0; z-index: 20000;
    background: rgba(0,0,0,0.7); justify-content: center; align-items: center;
  }
  #stats-overlay.visible, #hot-overlay.visible { display: flex; }
  .hot-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #222; }
  .hot-row .hot-rank { color: #888; width: 28px; font-weight: 700; }
  .hot-row .hot-name { flex: 1; }
  .hot-row .hot-name a { color: #58a6ff; text-decoration: none; }
  .hot-row .hot-name a:hover { text-decoration: underline; }
  .hot-row .hot-domain { color: #888; font-size: 12px; margin: 0 12px; }
  .hot-row .hot-stars { color: #eab308; white-space: nowrap; }
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
    .story-card { min-width: 160px; padding: 8px 12px; }
    .story-icon { font-size: 18px; }
    .story-text { font-size: 11px; }
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

<div id="stories">
  <div class="story-card" onclick="jumpToStory('Neural Radiance Fields & 3D Gaussian Splatting','NeRF')">
    <div class="story-icon">🔥</div>
    <div class="story-text"><b>NeRF → 3DGS</b><br>2 years, 22 descendants — the paradigm shift in 3D</div>
  </div>
  <div class="story-card" onclick="jumpToStory('Image Matching & Feature Detection','SIFT')">
    <div class="story-icon">🔗</div>
    <div class="story-text"><b>SIFT → DUSt3R → VGGT</b><br>20 years of image matching evolution</div>
  </div>
  <div class="story-card" onclick="jumpToStory('Robot Control','PID')">
    <div class="story-icon">🤖</div>
    <div class="story-text"><b>PID (1922) → Diffusion Policy</b><br>100 years of robot control</div>
  </div>
  <div class="story-card" onclick="jumpToStory('LiDAR Odometry & SLAM','ICP')">
    <div class="story-icon">📡</div>
    <div class="story-text"><b>ICP → LOAM → KISS-ICP</b><br>30 years of LiDAR SLAM</div>
  </div>
  <div class="story-card" onclick="jumpToStory('Large Language Models','Transformer')">
    <div class="story-icon">🧠</div>
    <div class="story-text"><b>Transformer → GPT-4 / DeepSeek</b><br>The LLM explosion from 2017</div>
  </div>
</div>

<div class="header">
  <h1>Robotics Technology Genealogy</h1>
  <div class="controls">
    <select id="category"></select>
    <select id="domain"></select>
    <input type="text" id="search" placeholder="Try: NeRF, SLAM, GPT-4, YOLO..." autocomplete="off" list="search-list">
    <datalist id="search-list"></datalist>
    <button class="filter-btn" id="btn-play" title="Watch technologies emerge year by year">&#9654; 1992→2026</button>
    <button class="filter-btn" id="btn-hot" title="Top trending methods in 2024-2025">&#128293; Hot</button>
    <button class="filter-btn" id="btn-oss" title="Show only open source methods">OSS Only</button>
    <button class="filter-btn" id="btn-stats" title="Show statistics">Stats</button>
    <span class="stats" id="stats"></span>
  </div>
  <a href="https://github.com/rsasaki0109/robotics-technology-genealogy" target="_blank">GitHub</a>
</div>

<div id="domain-banner">
  <div class="desc" id="banner-desc"></div>
  <div class="chips" id="banner-chips"></div>
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
    <div id="info-next" style="margin-top:8px; display:none; color:#22c55e; font-size:13px"></div>
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

<div id="hot-overlay">
  <div class="stats-panel">
    <button class="close-btn" onclick="toggleHotPanel()">&times;</button>
    <h2>&#128293; 2025 Hot Methods</h2>
    <p style="color:#888;margin-bottom:16px;font-size:13px">Top recent methods (2024+) ranked by GitHub stars</p>
    <div id="hot-list"></div>
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

  // "Read next" - find children (methods that extend this one)
  const nextEl = document.getElementById("info-next");
  if (nextEl && currentGraphData) {
    const children = currentGraphData.edges
      .filter(e => e.from === nodeData.id)
      .map(e => {
        const child = currentGraphData.nodes.find(n => n.id === e.to);
        return child ? { name: child.id, year: child.year, relation: e.title } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.year - b.year);

    if (children.length > 0) {
      nextEl.innerHTML = "<b>Read next:</b> " + children.map(c => {
        const safeName = c.name.replace(/"/g, "&quot;");
        return '<span class="next-link" onclick="searchAndFocus(&quot;' + safeName + '&quot;)">' +
        c.name + " [" + c.year + "]</span>";
      }
      ).join(", ");
      nextEl.style.display = "block";
    } else {
      nextEl.innerHTML = "<b>Leaf node</b> — no known descendants yet";
      nextEl.style.display = "block";
    }
  }

  panel.classList.add("visible");
}

function searchAndFocus(name) {
  if (network) {
    network.selectNodes([name]);
    network.focus(name, { scale: 1.2, animation: { duration: 500 } });
    const nodeData = currentGraphData.nodes.find(n => n.id === name);
    if (nodeData) showInfoPanel(nodeData);
  }
}

function toggleFilter(key, btnId) {
  filters[key] = !filters[key];
  // nopaper and paper are mutually exclusive
  if (key === "paper" && filters.paper) filters.nopaper = false;
  if (key === "nopaper" && filters.nopaper) filters.paper = false;
  document.getElementById("btn-oss").classList.toggle("active", filters.oss);
  if (currentGraphData) renderGraph(currentGraphData, false);
}

function jumpToStory(domainName, methodName) {
  // Find category
  for (const [catName, catData] of Object.entries(DATA.categories)) {
    if (catData.domain_names.includes(domainName)) {
      document.getElementById("category").value = catName;
      populateDomains(catName);
      document.getElementById("domain").value = domainName;
      renderGraph(DATA.domains[domainName].graph);
      showBanner(domainName);
      // Focus on the method
      setTimeout(() => {
        if (network) {
          network.selectNodes([methodName]);
          network.focus(methodName, { scale: 1.0, animation: { duration: 600 } });
        }
      }, 400);
      break;
    }
  }
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

function showBanner(domainName) {
  const banner = document.getElementById("domain-banner");
  const desc = document.getElementById("banner-desc");
  const chips = document.getElementById("banner-chips");

  if (!domainName || domainName === "__category__") {
    banner.classList.remove("visible");
    document.getElementById("graph").style.height = "calc(100vh - 70px)";
    return;
  }

  const d = DATA.domains[domainName];
  if (!d || !d.highlights) {
    banner.classList.remove("visible");
    return;
  }

  const h = d.highlights;
  desc.textContent = d.description ? d.description.trim().split("\\n")[0] : "";

  chips.innerHTML =
    '<span class="chip">' + h.year_range + '</span>' +
    '<span class="chip star"><b>' + h.top_star.name + '</b> ★' + h.top_star.stars.toLocaleString() + '</span>' +
    '<span class="chip latest"><b>' + h.latest.name + '</b> [' + h.latest.year + '] newest</span>' +
    '<span class="chip oss">OSS ' + h.oss_ratio + '</span>' +
    (h.roots.length ? '<span class="chip">Roots: ' + h.roots.join(", ") + '</span>' : '');

  banner.classList.add("visible");
  document.getElementById("graph").style.height = "calc(100vh - 110px)";
}

function onCategoryChange() {
  const catName = document.getElementById("category").value;
  populateDomains(catName);
  renderGraph(DATA.categories[catName].graph);
  showBanner(null);
}

function onDomainChange() {
  const catName = document.getElementById("category").value;
  const domainName = document.getElementById("domain").value;
  if (domainName === "__category__") {
    renderGraph(DATA.categories[catName].graph);
    showBanner(null);
  } else {
    renderGraph(DATA.domains[domainName].graph);
    showBanner(domainName);
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

let playTimer = null;
function playTimeline() {
  if (playTimer) { stopTimeline(); return; }
  if (!currentGraphData) return;
  const btn = document.getElementById("btn-play");
  btn.textContent = "\\u23f9 Stop";
  btn.classList.add("active");

  const nodesByYear = {};
  currentGraphData.nodes.forEach(n => {
    const y = n.year || 2020;
    if (!nodesByYear[y]) nodesByYear[y] = [];
    nodesByYear[y].push(n);
  });
  const years = Object.keys(nodesByYear).sort();

  const container = document.getElementById("graph");
  const visNodes = new vis.DataSet();
  const visEdges = new vis.DataSet();
  if (network) network.destroy();
  network = new vis.Network(container, {nodes: visNodes, edges: visEdges}, OPTIONS);

  let i = 0;
  playTimer = setInterval(() => {
    if (i >= years.length) { stopTimeline(); return; }
    const year = years[i];
    const newNodes = nodesByYear[year];
    // Highlight new nodes briefly
    const highlighted = newNodes.map(n => ({...n, size: (n.size || 25) * 1.6}));
    visNodes.add(highlighted);
    setTimeout(() => {
      newNodes.forEach(n => { visNodes.update({id: n.id, size: n.size || 25}); });
    }, 500);
    // Add edges where both endpoints exist
    const nodeIds = new Set(visNodes.getIds());
    currentGraphData.edges.forEach(e => {
      const edgeId = e.from + "->" + e.to;
      if (nodeIds.has(e.from) && nodeIds.has(e.to) && !visEdges.get(edgeId)) {
        visEdges.add({...e, id: edgeId});
      }
    });
    document.getElementById("stats").textContent = year + " \\u2014 " + visNodes.length + " methods";
    i++;
  }, 800);
}
function stopTimeline() {
  if (playTimer) { clearInterval(playTimer); playTimer = null; }
  document.getElementById("btn-play").textContent = "\\u25b6 Play";
  document.getElementById("btn-play").classList.remove("active");
  renderGraph(currentGraphData, false);
}

function toggleHotPanel() {
  const overlay = document.getElementById("hot-overlay");
  const btn = document.getElementById("btn-hot");
  const isVisible = overlay.classList.toggle("visible");
  btn.classList.toggle("active", isVisible);
}

function renderHotPanel() {
  if (!DATA || !DATA.hot_2025) return;
  const list = document.getElementById("hot-list");
  list.innerHTML = "";
  DATA.hot_2025.forEach((m, idx) => {
    const link = m.code
      ? '<a href="https://github.com/' + m.code + '" target="_blank">' + m.name + '</a>'
      : (m.arxiv ? '<a href="https://arxiv.org/abs/' + m.arxiv + '" target="_blank">' + m.name + '</a>' : m.name);
    list.innerHTML += '<div class="hot-row">' +
      '<span class="hot-rank">#' + (idx + 1) + '</span>' +
      '<span class="hot-name">' + link + ' <span style="color:#888">(' + m.year + ')</span></span>' +
      '<span class="hot-domain">' + m.domain + '</span>' +
      '<span class="hot-stars">\\u2605 ' + m.stars.toLocaleString() + '</span>' +
      '</div>';
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
    document.getElementById("btn-stats").addEventListener("click", () => toggleStatsPanel());
    document.getElementById("btn-play").addEventListener("click", playTimeline);
    document.getElementById("btn-hot").addEventListener("click", () => toggleHotPanel());
    const searchInput = document.getElementById("search");
    searchInput.addEventListener("change", (e) => { searchMethod(e.target.value); e.target.value = ""; });
    searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { searchMethod(e.target.value); e.target.value = ""; } });
    buildSearchIndex();
    renderHotPanel();
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
