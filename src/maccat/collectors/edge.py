"""EdgeCollector — thin subclass of ChromiumBaseCollector for Microsoft Edge.

All profile-scan logic lives in chromium.py. This module provides Edge-specific
paths, section title, and component denylist.
"""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["EdgeCollector", "EDGE_COMPONENT_DENYLIST"]

# Edge-specific component extension IDs.
# NOTE: Microsoft publishes no canonical component-ID list.
# This constant starts empty; COMPONENT_DENYLIST (the Chrome baseline) is applied
# via union in _denylist. Expand by installing Edge, opening edge://extensions,
# and cross-referencing IDs present on disk in Default/Extensions/ that are invisible
# in the UI (those are component IDs).
# Over-listing user extensions is the failure mode — do not block on completeness.
# Known gap: see STATE.md Deferred Items 'Edge denylist'.
EDGE_COMPONENT_DENYLIST: frozenset[str] = frozenset()

_BASE = Path.home() / "Library/Application Support/Microsoft Edge"
_TITLE = "Microsoft Edge Extensions"


class EdgeCollector(ChromiumBaseCollector):
    """Thin subclass — Edge-specific paths and denylist."""

    _base = _BASE
    _title = _TITLE
    _denylist = COMPONENT_DENYLIST | EDGE_COMPONENT_DENYLIST
    _browser_name = "Microsoft Edge"
