"""ChromiumBaseCollector — shared Chromium extension scan base class.

Parameterized by browser name, base path, and component denylist.
Subclasses (Chrome, Edge, Brave) override _base, _title, _denylist, and
_browser_name only.
"""
from __future__ import annotations

import sys
from pathlib import Path

from maccat.catalog.format import emit_item, version_sort_tail
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.chrome_name import chrome_ext_name
from maccat.helpers.json_io import json_get

__all__ = ["ChromiumBaseCollector", "COMPONENT_DENYLIST"]

# Component extensions pre-installed by Chrome — excluded from output.
# Source: update-list.sh:2078–2087 (denylist of 10 IDs — never a file, never an env var).
COMPONENT_DENYLIST: frozenset[str] = frozenset({
    "nmmhkkegccagdldgiimedpiccmgmieda",
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi",
    "aapocclcgogkmnckokdopfmhonfmgoek",
    "blpcfgokakmgnkcojhhkbfbldkacnbeo",
    "felcaaldnbdncclmgdcncolpebgiejap",
    "aohghmighlieiainnegkcijnfilokake",
    "apdfllckaahabafndbhieahigkjlhalf",
    "pjkljhegncpnkpknbcohdijeoejaedia",
    "mhjfbmdgcfjbbpaeojofohoefgiehjai",
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm",
})


class ChromiumBaseCollector(Collector):
    """Shared Chromium extension scan, parameterized by browser name and base path.

    Subclasses override _base, _title, and _denylist only.
    """

    _base: Path = Path()
    _title: str = ""
    _denylist: frozenset[str] = frozenset()
    _browser_name: str = ""

    def _collect_profile(self, extensions_dir: Path) -> list[str]:
        """Collect emit_item lines from one Chrome profile's Extensions directory."""
        items: list[str] = []
        # CAT-06: TOCTOU / unreadable entry degrades (zsh `ls ... 2>/dev/null`); skip profile.
        try:
            ext_dirs = list(extensions_dir.iterdir())
        except OSError:
            return items
        for ext_dir in ext_dirs:
            if not ext_dir.is_dir():
                continue
            ext_id = ext_dir.name
            # Skip Chrome internals (Temp, _metadata, etc.) and component extensions
            if ext_id == "Temp" or ext_id.startswith("_") or ext_id in self._denylist:
                continue
            # Version directory selection via sort -V | tail -1 (Phase 13 helper)
            try:
                candidates = [d.name for d in ext_dir.iterdir() if d.is_dir()]
            except OSError:
                continue
            ver_dir = version_sort_tail(candidates)
            if not ver_dir:
                continue
            manifest = ext_dir / ver_dir / "manifest.json"
            if not manifest.is_file():
                continue
            # Phase 13 helpers — do NOT reimplement
            name = chrome_ext_name(manifest)
            version = json_get(manifest, "version")
            line = emit_item(name, version, ext_id)
            if line:
                items.append(line)
        return items

    def collect(self) -> CollectorResult:
        """Enumerate all Chromium profiles and collect installed extensions."""
        if not self._base.is_dir():
            print(f"  NOTE: {self._browser_name} not installed.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=self._title, items=[])])

        all_items: list[str] = []

        # Profile enumeration: Default first, then sorted "Profile *" dirs (zsh :2089)
        profile_dirs: list[Path] = [self._base / "Default"]
        profile_dirs += sorted(self._base.glob("Profile */"))

        for profile in profile_dirs:
            ext_root = profile / "Extensions"
            if not ext_root.is_dir():
                continue
            all_items.extend(self._collect_profile(ext_root))

        # raw=False: Phase 16 orchestrator calls flush_section for cross-profile dedup
        return CollectorResult(sections=[Section(title=self._title, items=all_items)])
