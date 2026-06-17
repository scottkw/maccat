from __future__ import annotations

import plistlib
import re
import subprocess
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.plist_version import get_plist_version

# ---------------------------------------------------------------------------
# Module-level constants — NOT inside class so tests can monkeypatch via
# patch.object(safari_mod, "_PLUGINKIT", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_TITLE = "Safari Extensions"
_PLUGINKIT = Path("/usr/bin/pluginkit")
_PLUGIN_POINT = "com.apple.Safari.web-extension"
_PATH_RE = re.compile(r"^\s*Path\s*=\s*(.+\.appex)\s*$")

__all__ = ["SafariCollector"]


def _parse_pluginkit_output(stdout: str) -> list[Path]:
    """Extract .appex bundle paths from pluginkit -mAvv verbose output.

    Each extension block contains an indented "Path = /path/to/foo.appex" line.
    Returns a list of Path objects, one per matched line. Never raises.
    """
    paths: list[Path] = []
    for line in stdout.splitlines():
        m = _PATH_RE.match(line)
        if m:
            paths.append(Path(m.group(1).strip()))
    return paths


def _read_appex_name(appex_path: Path, bundle_id: str) -> str:
    """Resolve the display name for a Safari extension .appex bundle.

    Resolution chain (per 29-CONTEXT.md §Entry fields):
      1. CFBundleDisplayName from the appex's own Info.plist
      2. CFBundleName from the appex's own Info.plist — ONLY if != "safari"
      3. CFBundleDisplayName from the parent app's Info.plist (three levels up)
      4. CFBundleName from the parent app's Info.plist — ONLY if != "safari"
      5. bundle_id as final fallback (name is never empty, never "safari")

    Never raises — returns bundle_id on any failure so the caller always
    gets a usable name string.
    """
    try:
        info_plist = appex_path / "Contents" / "Info.plist"
        if not info_plist.is_file():
            return bundle_id
        with info_plist.open("rb") as fh:
            plist_data = plistlib.load(fh)
        if not isinstance(plist_data, dict):
            return bundle_id
        name = plist_data.get("CFBundleDisplayName", "")
        if isinstance(name, str):
            name = name.strip()
        else:
            name = ""
        if name:
            return name
        # Fallback: the appex's OWN CFBundleName (rejecting the generic
        # binary name "safari") before walking up to the parent app.
        own_name = plist_data.get("CFBundleName", "")
        if (
            isinstance(own_name, str)
            and own_name.strip()
            and own_name.strip().lower() != "safari"
        ):
            return own_name.strip()
        # Fallback: parent app plist (appex → PlugIns → Contents → app bundle)
        parent_plist_path = (
            appex_path.parent.parent.parent / "Contents" / "Info.plist"
        )
        if parent_plist_path.is_file():
            with parent_plist_path.open("rb") as pfh:
                parent = plistlib.load(pfh)
            if isinstance(parent, dict):
                parent_display = parent.get("CFBundleDisplayName", "")
                if isinstance(parent_display, str) and parent_display.strip():
                    return parent_display.strip()
                parent_bundle = parent.get("CFBundleName", "")
                if (
                    isinstance(parent_bundle, str)
                    and parent_bundle.strip()
                    and parent_bundle.strip().lower() != "safari"
                ):
                    return parent_bundle.strip()
    except Exception:  # noqa: BLE001
        pass
    return bundle_id


class SafariCollector(Collector):
    """Collect user-installed Safari extensions — BRW-04.

    Shells to ``pluginkit -mAvv -p com.apple.Safari.web-extension`` to
    enumerate every installed Safari web extension, then reads each
    ``<bundle>.appex/Contents/Info.plist`` via plistlib to extract:

      - name:    CFBundleDisplayName (with parent-app fallback chain)
      - version: CFBundleShortVersionString via get_plist_version (never-raising)
      - id:      CFBundleIdentifier

    Emits ``name (version) [id]`` lines via emit_item, routed through
    flush_section (sorted, deduped, ``(none found)`` when empty). Never raises.
    """

    def available(self) -> bool:
        """Return True only when /usr/bin/pluginkit exists on this machine."""
        return _PLUGINKIT.is_file()

    def collect(self) -> CollectorResult:
        """Collect Safari extensions, returning a single-section CollectorResult.

        Graceful degradation:
          - pluginkit absent → NOTE + empty section
          - pluginkit fails (OSError) → WARNING + empty section
          - non-zero exit → WARNING + empty section
          - empty stdout → empty section (no warning — zero extensions is normal)
          - per-extension plist unreadable → that extension skipped; others proceed
        """
        if not _PLUGINKIT.is_file():
            print("  NOTE: pluginkit not found.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        try:
            result = subprocess.run(
                [str(_PLUGINKIT), "-mAvv", "-p", _PLUGIN_POINT],
                capture_output=True,
                text=True,
                shell=False,
            )
        except OSError as exc:
            print(
                f"  WARNING: could not run pluginkit: {exc}",
                file=sys.stderr,
            )
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        if result.returncode != 0:
            print(
                f"  WARNING: pluginkit failed (exit {result.returncode}).",
                file=sys.stderr,
            )
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        if not result.stdout.strip():
            # Zero extensions installed — normal; no warning
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])

        appex_paths = _parse_pluginkit_output(result.stdout)
        items: list[str] = []

        for appex_path in appex_paths:
            try:
                info_plist = appex_path / "Contents" / "Info.plist"
                with info_plist.open("rb") as fh:
                    plist_data = plistlib.load(fh)
                if not isinstance(plist_data, dict):
                    continue
                id_ = plist_data.get("CFBundleIdentifier", "")
                if not isinstance(id_, str):
                    id_ = ""
                id_ = id_.strip()
                if not id_:
                    continue
                name = _read_appex_name(appex_path, id_)
                version = get_plist_version(info_plist)
                line = emit_item(name, version, id_)
                if line:
                    items.append(line)
            except Exception:  # noqa: BLE001
                continue  # single bad plist never aborts the whole collection

        return CollectorResult(sections=[Section(title=_TITLE, items=items)])
