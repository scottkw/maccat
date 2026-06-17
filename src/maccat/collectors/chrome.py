"""ChromeCollector — thin subclass of ChromiumBaseCollector for Google Chrome.

All profile-scan logic lives in chromium.py. This module provides Chrome-specific
paths, section title, and component denylist, and re-exports COMPONENT_DENYLIST
for backward compatibility.
"""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["ChromeCollector", "COMPONENT_DENYLIST"]  # re-export for backward compat

_BASE = Path.home() / "Library/Application Support/Google/Chrome"
_TITLE = "Google Chrome Extensions"


class ChromeCollector(ChromiumBaseCollector):
    """Thin subclass — Chrome-specific paths and denylist only."""

    _base = _BASE
    _title = _TITLE
    _denylist = COMPONENT_DENYLIST
    _browser_name = "Google Chrome"
