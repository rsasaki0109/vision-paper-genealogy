"""Tests for domain YAML integrity."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from robotics_technology_genealogy.models import load_all_domains

DOMAINS_DIR = Path(__file__).parent.parent / "domains"

VALID_RELATION_TYPES = {"extends", "combines", "replaces", "inspires"}
REQUIRED_METHOD_FIELDS = {"name", "year", "description"}


def _load_raw_yamls() -> list[tuple[str, dict]]:
    """Load all YAML files as raw dicts for field-level checks."""
    results = []
    for path in sorted(DOMAINS_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f)
        results.append((path.name, data))
    return results


# ---- Tests ----


def test_all_yaml_parseable():
    """Every YAML in domains/ must parse without errors."""
    for path in sorted(DOMAINS_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{path.name} did not parse to a dict"


def test_all_methods_have_required_fields():
    """Each method must have name, year, and description."""
    for filename, data in _load_raw_yamls():
        for i, method in enumerate(data.get("methods", [])):
            for field in REQUIRED_METHOD_FIELDS:
                assert field in method, (
                    f"{filename}: method #{i} ({method.get('name', '???')}) missing '{field}'"
                )
                assert method[field] is not None, (
                    f"{filename}: method '{method.get('name', '???')}' has null '{field}'"
                )


def test_relation_types_valid():
    """All relation values must be extends/combines/replaces/inspires."""
    for filename, data in _load_raw_yamls():
        for method in data.get("methods", []):
            for parent in method.get("parents", []):
                relation = parent.get("relation", "extends")
                assert relation in VALID_RELATION_TYPES, (
                    f"{filename}: method '{method['name']}' has invalid relation '{relation}'"
                )


def test_parent_references_exist():
    """If a method lists a parent, that parent must exist in the same domain."""
    for filename, data in _load_raw_yamls():
        method_names = {m["name"] for m in data.get("methods", [])}
        for method in data.get("methods", []):
            for parent in method.get("parents", []):
                assert parent["name"] in method_names, (
                    f"{filename}: method '{method['name']}' references unknown parent "
                    f"'{parent['name']}'"
                )


def test_no_duplicate_methods_in_domain():
    """No two methods in the same domain file should share a name."""
    for filename, data in _load_raw_yamls():
        names = [m["name"] for m in data.get("methods", [])]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, (
            f"{filename}: duplicate method names: {duplicates}"
        )


def test_year_reasonable():
    """All years must be between 1950 and 2030."""
    for filename, data in _load_raw_yamls():
        for method in data.get("methods", []):
            year = method.get("year")
            assert year is not None, (
                f"{filename}: method '{method['name']}' has no year"
            )
            assert 1900 <= year <= 2030, (
                f"{filename}: method '{method['name']}' has unreasonable year {year}"
            )


def test_github_urls_format():
    """If code field exists and is non-empty, it should look like 'owner/repo'."""
    pattern = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
    for filename, data in _load_raw_yamls():
        for method in data.get("methods", []):
            code = method.get("code")
            if code:  # skip None or empty string
                assert pattern.match(code), (
                    f"{filename}: method '{method['name']}' has malformed code field "
                    f"'{code}' (expected 'owner/repo')"
                )
