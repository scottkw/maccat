"""ZedCollector — Zed extensions from ~/Library/Application Support/Zed/extensions/index.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

__all__ = ["ZedCollector"]

# ---------------------------------------------------------------------------
# Module-level constants — NOT inside class so tests can monkeypatch via
# patch.object(zed_mod, "_INDEX", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_INDEX = Path.home() / "Library/Application Support/Zed/extensions/index.json"
_TITLE = "Zed Extensions"


class ZedCollector(Collector):
    """1-section collector for Zed extensions.

    Source of truth: ~/Library/Application Support/Zed/extensions/index.json

    Filter: entries with ``"dev": true`` are excluded (locally-developed extensions
    that are not restorable from a catalog snapshot — BRW-03).

    Entry format: ``name (version) [id]`` via emit_item.

    Degrades gracefully: if index.json is absent or unreadable, returns items=[] with
    a NOTE to stderr.  Never raises.
    """

    def collect(self) -> CollectorResult:
        """Return 1 section: 'Zed Extensions'."""
        if not _INDEX.is_file():
            print("  NOTE: Zed not installed.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        try:
            data = json.loads(_INDEX.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        items: list[str] = []
        for ext_id, info in data.get("extensions", {}).items():
            # CAT-06: non-dict entry degrades; skip.
            if not isinstance(info, dict):
                continue
            # BRW-03: exclude dev (locally-developed / non-restorable) extensions.
            if info.get("dev"):
                continue
            manifest = info.get("manifest", {})
            if not isinstance(manifest, dict):
                manifest = {}
            name: str = manifest.get("name", ext_id)
            version: str = manifest.get("version", "")
            line = emit_item(name, version, ext_id)
            if line:
                items.append(line)

        return CollectorResult(sections=[Section(title=_TITLE, items=items)])
