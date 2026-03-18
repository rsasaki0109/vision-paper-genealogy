"""Data models for vision paper genealogy."""

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
