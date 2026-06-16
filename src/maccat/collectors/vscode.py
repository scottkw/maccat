"""VSCodeCollector and shared _collect_editor_extensions helper.

Byte-parity with update-list.sh:1387 (collect_vscode_extensions).
CursorCollector in cursor.py reuses this helper.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.vsc_name import resolve_vsc_ext_name

__all__ = ["VSCodeCollector", "_collect_editor_extensions"]


def _collect_editor_extensions(
    ext_dir: Path,
    cli_name: str,
    section_title: str,
) -> tuple[list[str], list[str]]:
    """Shared logic for VS Code and Cursor. Returns (items, warnings).

    Path A: CLI --list-extensions --show-versions (preferred)
    Path B: extensions.json fallback (when CLI absent or returns empty)
    """
    ext_json = ext_dir / "extensions.json"
    items: list[str] = []
    warnings: list[str] = []

    # Path A — CLI (preferred)
    cli_lines: list[str] = []
    if shutil.which(cli_name):
        result = subprocess.run(
            [cli_name, "--list-extensions", "--show-versions"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            cli_lines = result.stdout.strip().splitlines()

    if cli_lines:
        # Load extensions.json for relativeLocation (needed for display name)
        ext_meta: dict[str, dict[str, object]] = {}
        if ext_json.is_file():
            try:
                entries = json.loads(ext_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []
            # CAT-06: non-list top level degrades (jq `.[]`); skip non-dict entries.
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    identifier = entry.get("identifier")
                    id_ = identifier.get("id", "") if isinstance(identifier, dict) else ""
                    if id_:
                        ext_meta[id_.lower()] = entry

        for raw in cli_lines:
            parts = raw.rsplit("@", 1)  # mirrors zsh ${line%@*} / ${line##*@} — last @ only
            if len(parts) != 2:
                continue
            id_, version = parts[0], parts[1]
            meta = ext_meta.get(id_.lower(), {})
            rel_loc = meta.get("relativeLocation", "")
            if rel_loc:
                pkg_json = ext_dir / str(rel_loc) / "package.json"
                display_name = resolve_vsc_ext_name(pkg_json, id_)
            else:
                display_name = id_  # Pitfall D: relativeLocation absent, use id directly
            line = emit_item(display_name, version, id_)
            if line:
                items.append(line)
        return items, warnings

    # Path B — extensions.json fallback
    if not ext_json.is_file():
        print(
            f"  NOTE: {cli_name.capitalize()} not installed or no extensions found.",
            file=sys.stderr,
        )
        return [], warnings

    # CLI present but returned empty — warn and fall back
    if shutil.which(cli_name):
        print(
            f"  WARNING: {cli_name} CLI returned empty list. Falling back to extensions.json.",
            file=sys.stderr,
        )
    try:
        entries = json.loads(ext_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], warnings
    # CAT-06: non-list top level degrades (jq `.[]`); skip non-dict entries.
    if not isinstance(entries, list):
        return [], warnings
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("identifier")
        id_ = identifier.get("id", "") if isinstance(identifier, dict) else ""
        if not id_:
            continue
        version = str(entry.get("version", ""))
        rel_loc = str(entry.get("relativeLocation", ""))
        pkg_json = ext_dir / rel_loc / "package.json"
        display_name = resolve_vsc_ext_name(pkg_json, id_)
        line = emit_item(display_name, version, id_)
        if line:
            items.append(line)
    return items, warnings


class VSCodeCollector(Collector):
    """Collect VS Code extensions.

    Zsh analog: update-list.sh lines 1387-1476 (collect_vscode_extensions).
    Uses CLI --list-extensions --show-versions (preferred) with extensions.json fallback.
    """

    TITLE = "VS Code Extensions"
    _EXT_DIR = Path.home() / ".vscode/extensions"

    def collect(self) -> CollectorResult:
        items, warnings = _collect_editor_extensions(self._EXT_DIR, "code", self.TITLE)
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=items)],
            warnings=warnings,
        )
