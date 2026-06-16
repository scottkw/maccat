"""FirefoxCollector — multi-profile at byte-parity with update-list.sh:2154
(collect_firefox_extensions). profiles.ini discovery, app-profile filter,
cross-profile dedup.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

__all__ = ["FirefoxCollector"]

_FF_DIR = Path.home() / "Library/Application Support/Firefox"
_TITLE = "Firefox Extensions"


class FirefoxCollector(Collector):
    """Collect all user-installed Firefox extensions across all profiles.

    Profile paths are discovered from profiles.ini using splitlines() (not split("\\n"))
    to handle CRLF line endings safely (Pitfall E).

    Location filter: only "app-profile" addons are included; "app-builtin" and
    "app-builtin-addons" (system add-ons) are excluded.

    All items are accumulated across all profiles; flush_section deduplication
    is performed once by the Phase 16 orchestrator (raw=False).
    """

    def _get_profile_paths(self) -> list[Path]:
        """Parse profiles.ini and return list of profile directory Paths."""
        profiles_ini = _FF_DIR / "profiles.ini"
        if not profiles_ini.is_file():
            return []
        paths: list[Path] = []
        # Pitfall E: use splitlines() not split("\n") — handles CRLF in profiles.ini
        for line in profiles_ini.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Path="):
                rel = line[len("Path="):]
                paths.append(_FF_DIR / rel)
        return paths

    def _collect_profile(self, profile_dir: Path) -> list[str]:
        """Collect emit_item lines from one Firefox profile's extensions.json."""
        ext_json = profile_dir / "extensions.json"
        if not ext_json.is_file():
            return []
        try:
            data = json.loads(ext_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        items: list[str] = []
        for addon in (data.get("addons") or []):
            # CAT-06: non-dict addon element degrades (jq degrades on errors); skip.
            # PARITY DEVIATION (intentional, WR-01): zsh's `jq` aborts the whole
            # section on the first non-object addon; this per-entry skip is more
            # robust (keeps valid neighbours). Only differs on malformed addon
            # lists that never occur in real data, so golden parity is unaffected.
            if not isinstance(addon, dict):
                continue
            # Location filter: only include user-installed extensions (app-profile)
            # Exclude: app-builtin, app-builtin-addons (system add-ons)
            if addon.get("location") != "app-profile":
                continue
            id_ = addon.get("id", "")
            if not id_ or id_ == "null":
                continue
            # CAT-06: non-dict defaultLocale degrades — `.get` only on a real dict.
            dl = addon.get("defaultLocale")
            name: str = (dl.get("name") if isinstance(dl, dict) else None) or id_
            version: str = addon.get("version", "")
            line = emit_item(name, version, id_)
            if line:
                items.append(line)
        return items

    def collect(self) -> CollectorResult:
        """Enumerate all Firefox profiles and collect installed extensions."""
        profiles_ini = _FF_DIR / "profiles.ini"
        if not profiles_ini.is_file():
            print("  NOTE: Firefox not installed.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        all_items: list[str] = []

        for profile_dir in self._get_profile_paths():
            all_items.extend(self._collect_profile(profile_dir))

        # raw=False: Phase 16 orchestrator calls flush_section for cross-profile dedup
        return CollectorResult(sections=[Section(title=_TITLE, items=all_items)])
