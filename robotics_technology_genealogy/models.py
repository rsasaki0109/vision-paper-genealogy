"""Data models for robotics paper genealogy."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel


class RelationType(str, Enum):
    extends = "extends"
    combines = "combines"
    replaces = "replaces"
    inspires = "inspires"


class Parent(BaseModel):
    name: str
    relation: RelationType = RelationType.extends


class OpenSourceStatus(str, Enum):
    open = "open"              # Fully open source (MIT, Apache-2.0, BSD, etc.)
    research = "research"      # Code available but restrictive license (non-commercial, research-only)
    partial = "partial"        # Weights/model closed, code open; or limited release
    closed = "closed"          # No public code/weights
    unknown = "unknown"        # Not sure


class Method(BaseModel):
    name: str
    paper: str | None = None
    arxiv: str | None = None
    year: int
    code: str | None = None
    stars: int | None = None
    tags: list[str] = []
    parents: list[Parent] = []
    description: str | None = None
    license: str | None = None                          # e.g. "MIT", "Apache-2.0", "CC-BY-NC-4.0"
    open_source: OpenSourceStatus | None = None         # open / research / partial / closed

    @property
    def inferred_open_source(self) -> OpenSourceStatus:
        """Infer open source status from available fields."""
        if self.open_source is not None:
            return self.open_source
        if self.code:
            return OpenSourceStatus.open
        return OpenSourceStatus.unknown

    @property
    def has_paper(self) -> bool:
        return bool(self.paper or self.arxiv)


class Domain(BaseModel):
    name: str
    description: str | None = None
    source_awesome_lists: list[str] = []
    methods: list[Method]


def load_domain(path: str | Path) -> Domain:
    """Load a domain definition from a YAML file."""
    path = Path(path)
    with path.open() as f:
        data = yaml.safe_load(f)
    return Domain(**data)


def load_all_domains(domains_dir: str | Path) -> list[Domain]:
    """Load all domain YAML files from a directory."""
    domains_dir = Path(domains_dir)
    domains = []
    for path in sorted(domains_dir.glob("*.yaml")):
        domains.append(load_domain(path))
    return domains
