"""Streamlit web app for vision-paper-genealogy."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from robotics_paper_genealogy.graph.builder import build_graph, build_graph_from_domains
from robotics_paper_genealogy.models import Domain, load_all_domains
from robotics_paper_genealogy.viz.web import export_html

DOMAINS_DIR = Path(__file__).parent.parent / "domains"


@st.cache_data
def load_domains() -> list[Domain]:
    return load_all_domains(DOMAINS_DIR)


def main() -> None:
    st.set_page_config(
        page_title="Robotics Paper Genealogy",
        page_icon="🌳",
        layout="wide",
    )

    st.title("Robotics Paper Genealogy")
    st.caption("Interactive genealogy tree of Computer Vision research methods")

    domains = load_domains()

    POINT_CLOUD_DOMAINS = {
        "LiDAR Odometry & SLAM",
        "Point Cloud Denoising",
        "Point Cloud Scene Flow",
        "3D Object Detection",
        "Visual Place Recognition",
    }
    VISUAL_DOMAINS = {
        "Neural Radiance Fields & 3D Gaussian Splatting",
        "Image Matching & Feature Detection",
        "Visual SLAM",
        "Depth Completion",
    }

    GROUPS = {
        "Point Cloud / LiDAR": [d for d in domains if d.name in POINT_CLOUD_DOMAINS],
        "Visual / Camera": [d for d in domains if d.name in VISUAL_DOMAINS],
        "All": domains,
    }

    col1, col2 = st.columns([1, 3])

    with col1:
        category = st.selectbox("Category", list(GROUPS.keys()))
        group_domains = GROUPS[category]
        domain_options = ["All"] + [d.name for d in group_domains]
        selected = st.selectbox("Domain", domain_options)

        if selected == "All":
            graph = build_graph_from_domains(group_domains)
        else:
            domain = next(d for d in group_domains if d.name == selected)
            graph = build_graph(domain)

        # Filters
        all_tags = sorted({tag for node in graph.nodes.values() for tag in node.method.tags})
        selected_tags = st.multiselect("Filter by tags", all_tags)

        all_years = sorted({node.method.year for node in graph.nodes.values()})
        year_range = st.slider(
            "Year range",
            min_value=min(all_years),
            max_value=max(all_years),
            value=(min(all_years), max(all_years)),
        )

        # Stats
        st.markdown("---")
        st.metric("Methods", len(graph.nodes))
        roots = graph.get_roots()
        st.metric("Root methods", len(roots))


    with col2:
        # Apply filters: rebuild graph with filtered methods
        if selected_tags or year_range != (min(all_years), max(all_years)):
            from robotics_paper_genealogy.graph.builder import GenealogyGraph

            filtered = GenealogyGraph()
            for name, node in graph.nodes.items():
                m = node.method
                if year_range[0] <= m.year <= year_range[1]:
                    if not selected_tags or any(t in m.tags for t in selected_tags):
                        filtered.add_method(m)
            # Also add parents of filtered methods so edges connect
            for name, node in list(filtered.nodes.items()):
                for parent_ref in node.method.parents:
                    if parent_ref.name in graph.nodes and parent_ref.name not in filtered.nodes:
                        filtered.add_method(graph.nodes[parent_ref.name].method)
            filtered.build_edges()
            display_graph = filtered
        else:
            display_graph = graph

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            export_html(display_graph, f.name, height="650px")
            html_content = Path(f.name).read_text()

        components.html(html_content, height=680, scrolling=True)

    # Method details panel
    st.markdown("---")
    method_names = sorted(graph.nodes.keys())
    selected_method = st.selectbox("Method details", ["(select)"] + method_names)

    if selected_method != "(select)":
        node = graph.nodes[selected_method]
        m = node.method

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"### {m.name}")
            if m.description:
                st.write(m.description)
            if m.paper:
                st.write(f"**Paper:** {m.paper}")
        with c2:
            if m.arxiv:
                st.write(f"**arXiv:** [{m.arxiv}](https://arxiv.org/abs/{m.arxiv})")
            if m.code:
                st.write(f"**Code:** [{m.code}](https://github.com/{m.code})")
            if m.stars:
                st.write(f"**Stars:** ★ {m.stars:,}")
        with c3:
            st.write(f"**Year:** {m.year}")
            if m.tags:
                st.write(f"**Tags:** {', '.join(m.tags)}")
            if node.parent_nodes:
                parents = ", ".join(f"{p.method.name} ({r.value})" for p, r in node.parent_nodes)
                st.write(f"**Parents:** {parents}")
            if node.children:
                children = ", ".join(f"{c.method.name} ({r.value})" for c, r in node.children)
                st.write(f"**Children:** {children}")


if __name__ == "__main__":
    main()
