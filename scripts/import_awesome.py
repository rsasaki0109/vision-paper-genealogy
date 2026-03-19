#!/usr/bin/env python3
"""Import an awesome list from GitHub and generate a skeleton YAML domain file.

Usage:
    python scripts/import_awesome.py https://github.com/someone/awesome-xxx --output domains/new_domain.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests


def github_raw_url(github_url: str) -> str:
    """Convert a GitHub repo URL to the raw README.md URL."""
    # Normalise: strip trailing slash, .git suffix
    url = github_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Extract owner/repo
    match = re.match(r"https?://github\.com/([^/]+/[^/]+)", url)
    if not match:
        raise ValueError(f"Not a valid GitHub URL: {github_url}")

    owner_repo = match.group(1)

    # Try common branches
    for branch in ("main", "master"):
        raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{branch}/README.md"
        resp = requests.head(raw_url, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            return raw_url

    raise RuntimeError(
        f"Could not find README.md on main or master branch for {owner_repo}"
    )


def fetch_readme(github_url: str) -> str:
    """Fetch the README.md content from a GitHub repo."""
    raw_url = github_raw_url(github_url)
    resp = requests.get(raw_url, timeout=30)
    resp.raise_for_status()
    return resp.text


# Patterns
YEAR_RE = re.compile(r"[\(\[]((?:19|20)\d{2})[\)\]]")
GITHUB_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
ARXIV_RE = re.compile(r"https?://arxiv\.org/abs/([\d.]+(?:v\d+)?)")

# Markdown link: [text](url)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_name_from_line(line: str) -> str | None:
    """Try to extract a paper/project name from a Markdown line."""
    # Prefer the first bold text: **Name**
    bold = re.search(r"\*\*([^*]+)\*\*", line)
    if bold:
        return bold.group(1).strip()

    # Otherwise use the first markdown link text
    link = MD_LINK_RE.search(line)
    if link:
        text = link.group(1).strip()
        # Skip generic link texts
        if text.lower() not in ("paper", "code", "project", "pdf", "github", "arxiv", "link"):
            return text

    return None


def parse_entries(readme: str) -> list[dict]:
    """Parse README content and extract entries with name, year, code, arxiv."""
    entries = []
    seen_names: set[str] = set()

    for line in readme.splitlines():
        stripped = line.strip()

        # Skip empty lines, headings-only, horizontal rules
        if not stripped or stripped.startswith("#") and "[" not in stripped:
            continue

        # We want lines that look like list items or table rows
        is_list = stripped.startswith(("-", "*", "|"))
        if not is_list:
            continue

        name = extract_name_from_line(stripped)
        if not name:
            continue

        # Deduplicate
        name_key = name.lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)

        year_match = YEAR_RE.search(stripped)
        github_match = GITHUB_RE.search(stripped)
        arxiv_match = ARXIV_RE.search(stripped)

        # Skip entries that have nothing useful
        if not year_match and not github_match and not arxiv_match:
            continue

        entry: dict[str, str | int | None] = {"name": name}
        entry["year"] = int(year_match.group(1)) if year_match else None

        if github_match:
            code = github_match.group(1)
            # Strip trailing .git or slash artefacts
            code = code.rstrip("/")
            if code.endswith(".git"):
                code = code[:-4]
            entry["code"] = code
        else:
            entry["code"] = None

        entry["arxiv"] = arxiv_match.group(1) if arxiv_match else None

        entries.append(entry)

    return entries


def entries_to_yaml(entries: list[dict], domain_name: str) -> str:
    """Convert entries to a skeleton YAML domain file."""
    lines = [
        f'name: "{domain_name}"',
        f'description: "Imported from awesome list - needs manual curation"',
        "methods:",
    ]

    for e in entries:
        lines.append(f'  - name: "{e["name"]}"')
        if e.get("year"):
            lines.append(f"    year: {e['year']}")
        else:
            lines.append("    year: 2024  # TODO: fill in correct year")
        if e.get("arxiv"):
            lines.append(f'    arxiv: "{e["arxiv"]}"')
        if e.get("code"):
            lines.append(f'    code: "{e["code"]}"')
        lines.append("    parents: []  # TODO: fill in relationships")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import an awesome list from GitHub into a skeleton YAML domain file."
    )
    parser.add_argument("url", help="GitHub URL of the awesome list repo")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output YAML file path (default: stdout)",
    )
    parser.add_argument(
        "--domain-name",
        default=None,
        help="Domain name for the YAML (default: derived from repo name)",
    )
    args = parser.parse_args()

    # Derive domain name from URL if not given
    if args.domain_name:
        domain_name = args.domain_name
    else:
        match = re.search(r"github\.com/[^/]+/(.+?)(?:\.git)?/?$", args.url)
        domain_name = match.group(1) if match else "New Domain"
        # Clean up: awesome-robotics -> Robotics
        domain_name = re.sub(r"^awesome-?", "", domain_name, flags=re.IGNORECASE)
        domain_name = domain_name.replace("-", " ").replace("_", " ").title()

    print(f"Fetching README from {args.url} ...", file=sys.stderr)
    readme = fetch_readme(args.url)
    print(f"README fetched ({len(readme)} bytes)", file=sys.stderr)

    entries = parse_entries(readme)
    print(f"Extracted {len(entries)} entries", file=sys.stderr)

    if not entries:
        print("No entries found. The README format may not be supported.", file=sys.stderr)
        sys.exit(1)

    yaml_content = entries_to_yaml(entries, domain_name)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_content)
        print(f"Written to {output_path}", file=sys.stderr)
    else:
        print(yaml_content)


if __name__ == "__main__":
    main()
