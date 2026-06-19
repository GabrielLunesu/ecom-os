"""Drift guard: the live catalog/capabilities must match the pinned conformance fixtures.

The compatibility hash and capability model are checked-in contracts (Runtime §17, AGENTS §9).
Any intentional tool/schema/capability change must regenerate these fixtures in the same change
set; an accidental change fails here loudly.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.hermes.capabilities import FEATURE_REQUIREMENTS, REQUIRED_FLAGS
from app.tools.generators import catalog_manifest

# backend/tests/ -> repo root -> hermes-integration/conformance
_FIXTURES = Path(__file__).resolve().parents[2] / "hermes-integration" / "conformance"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_catalog_manifest_matches_pinned() -> None:
    pinned = _load("catalog-manifest.json")
    live = catalog_manifest()
    assert live["catalog_version"] == pinned["catalog_version"]
    assert live["compatibility_hash"] == pinned["compatibility_hash"], (
        "catalog compatibility hash changed — regenerate "
        "hermes-integration/conformance/catalog-manifest.json and review schema changes"
    )
    assert live["tools"] == pinned["tools"]


def test_required_flags_match_pinned() -> None:
    pinned = _load("capabilities.json")
    assert sorted(REQUIRED_FLAGS) == sorted(pinned["required_flags"])


def test_feature_requirements_match_pinned() -> None:
    pinned = _load("capabilities.json")["features"]
    live = {
        name: {
            "mandatory": sorted(req.mandatory),
            "optional": sorted(req.optional),
        }
        for name, req in FEATURE_REQUIREMENTS.items()
    }
    expected = {
        name: {
            "mandatory": sorted(spec["mandatory"]),
            "optional": sorted(spec["optional"]),
        }
        for name, spec in pinned.items()
    }
    assert live == expected
