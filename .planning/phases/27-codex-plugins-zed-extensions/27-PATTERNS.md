# Phase 27: Codex Plugins + Zed Extensions - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/maccat/collectors/codex.py` (MODIFY) | collector | request-response + file-I/O | `src/maccat/collectors/claude.py` (multi-section pattern) + existing `codex.py` (CLI+TOML pattern) | exact |
| `src/maccat/collectors/zed.py` (CREATE) | collector | file-I/O | `src/maccat/collectors/firefox.py` (single-section JSON file read) | exact |
| `src/maccat/collectors/__init__.py` (MODIFY) | registry config | — | existing `__init__.py` (extend `get_registry()` after `CursorCollector`) | exact |
| `tests/collectors/test_codex.py` (MODIFY) | test | — | existing `tests/collectors/test_codex.py` + `test_claude.py` (multi-section test pattern) | exact |
| `tests/collectors/test_zed.py` (CREATE) | test | — | `tests/collectors/test_firefox.py` (single-section JSON collector test pattern) | exact |
| `tests/collectors/test_registry.py` or `tests/test_titles.py` (CREATE) | test | — | no existing uniqueness test; use multi-import pattern from `test_claude.py` / `test_codex.py` | partial |

---

## Pattern Assignments

### `src/maccat/collectors/codex.py` (MODIFY — add second section)

**Primary analog for multi-section shape:** `src/maccat/collectors/claude.py`

**Secondary analog for CLI+TOML-header discipline:** existing `src/maccat/collectors/codex.py` (the `_collect_via_cli` / `_collect_via_toml` pattern already present)

#### Multi-section `collect()` pattern (from `claude.py` lines 177–185):
```python
def collect(self) -> CollectorResult:
    """Return all three Claude sections in fixed order."""
    return CollectorResult(
        sections=[
            self._collect_plugins(),
            self._collect_mcp(),
            self._collect_skills_agents(),
        ]
    )
```
**Apply to `codex.py`:** rename existing single-section logic to `_collect_mcp() -> Section`, add `_collect_plugins() -> Section`, then:
```python
def collect(self) -> CollectorResult:
    return CollectorResult(
        sections=[
            self._collect_mcp(),
            self._collect_plugins(),
        ]
    )
```

#### Sub-collector returning `Section` (from `claude.py` lines 75–100, `_collect_plugins`):
```python
def _collect_plugins(self) -> Section:
    if not _PLUGINS_PATH.is_file():
        return Section(title=self._PLUGINS_TITLE, items=[])
    try:
        data = json.loads(_PLUGINS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Section(title=self._PLUGINS_TITLE, items=[])
    items: list[str] = []
    ...
    return Section(title=self._PLUGINS_TITLE, items=items)
```
**Key difference for codex plugins:** sub-collectors return `Section` (not `CollectorResult`). The MCP section's existing `collect()` body becomes `_collect_mcp() -> Section` — same logic, return type changes from `CollectorResult(sections=[Section(...)])` to `Section(...)`.

#### Module-level TITLE constant (from `codex.py` lines 22–24):
```python
_TITLE = "Codex MCP Servers"
_TOML_PATH = Path.home() / ".codex/config.toml"
```
**Add for plugins section (new constant, same module-level placement):**
```python
_PLUGINS_TITLE = "Codex Plugins"
_PLUGINS_TOML_PATH = Path.home() / ".codex/config.toml"  # same file, different header pattern
```

#### TOML header-grep pattern (from `codex.py` lines 79–99 — copy exactly for plugins, change regex):
```python
def _collect_via_toml(self) -> list[str]:
    try:
        text = _TOML_PATH.read_text(encoding="utf-8")
    except OSError:
        return []
    items: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\[mcp_servers\.(.*)\]$", line.strip())
        if m:
            name = m.group(1).strip('"')
            transport = "stdio"  # default — value lines are never read (CAT-05)
            item = emit_item(name, "", transport)
            if item:
                items.append(item)
    return items
```
**For plugins:** change regex to `r'^\[plugins\."?([^"\]]+)"?\]$'`. Never call `tomllib.loads()`. Extract name/id from header only — `emit_item(name, "", id_)` where id_ is the full `name@marketplace` key or just the bare name.

#### CLI guard pattern (from `codex.py` lines 44–77):
```python
result = subprocess.run(
    ["codex", "mcp", "list", "--json"],
    capture_output=True,
    text=True,
    shell=False,
)
if result.returncode != 0 or not result.stdout.strip():
    return []
try:
    entries = json.loads(result.stdout)
except json.JSONDecodeError:
    return []
if not isinstance(entries, list) or not entries:
    return []
```
**For plugins CLI:** change command to `["codex", "plugin", "list", "--json"]`. Same returncode/stderr guard. Parse `pluginId` or `name` field — `emit_item(name, "", plugin_id)`.

---

### `src/maccat/collectors/zed.py` (CREATE)

**Analog:** `src/maccat/collectors/firefox.py` (single-section JSON-file collector)

#### File header and imports pattern (from `firefox.py` lines 1–17):
```python
"""FirefoxCollector — multi-profile at byte-parity with ..."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

__all__ = ["FirefoxCollector"]

_FF_DIR = Path.home() / "Library/Application Support/Firefox"
_TITLE = "Firefox Extensions"
```
**For `zed.py`:** same pattern, swap constants:
```python
"""ZedCollector — Zed extensions from index.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

__all__ = ["ZedCollector"]

_INDEX = Path.home() / "Library/Application Support/Zed/extensions/index.json"
_TITLE = "Zed Extensions"
```

#### NOTE-to-stderr + empty section on absent file (from `firefox.py` lines 80–86):
```python
def collect(self) -> CollectorResult:
    profiles_ini = _FF_DIR / "profiles.ini"
    if not profiles_ini.is_file():
        print("  NOTE: Firefox not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```
**For Zed:**
```python
def collect(self) -> CollectorResult:
    if not _INDEX.is_file():
        print("  NOTE: Zed not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```

#### JSON parse with graceful degradation (from `firefox.py` lines 51–55):
```python
try:
    data = json.loads(ext_json.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    return []
```
**For Zed:** same try/except block; on exception return `CollectorResult(sections=[Section(title=_TITLE, items=[])])` directly from `collect()`.

#### emit_item call pattern (from `firefox.py` lines 73–77):
```python
line = emit_item(name, version, id_)
if line:
    items.append(line)
```
**For Zed:** `emit_item(name, version, ext_id)` → `"name (version) [ext_id]"`.

#### Full Zed iteration shape (from RESEARCH.md reconciliation #1, adapted to codebase style):
```python
for ext_id, info in data.get("extensions", {}).items():
    if info.get("dev"):          # FMT-03: exclude dev (non-restorable) extensions
        continue
    if not isinstance(info, dict):
        continue
    manifest = info.get("manifest", {})
    if not isinstance(manifest, dict):
        manifest = {}
    name = manifest.get("name", ext_id)
    version = manifest.get("version", "")
    line = emit_item(name, version, ext_id)
    if line:
        items.append(line)
```

---

### `src/maccat/collectors/__init__.py` (MODIFY — add ZedCollector after CursorCollector)

**Analog:** existing `src/maccat/collectors/__init__.py` lines 12–70

#### Deferred-import pattern (lines 42–53):
```python
from maccat.collectors.chrome import ChromeCollector
from maccat.collectors.claude import ClaudeCollector
from maccat.collectors.codex import CodexCollector
from maccat.collectors.cursor import CursorCollector
from maccat.collectors.firefox import FirefoxCollector
...
```
**Add after `CursorCollector` import:**
```python
from maccat.collectors.zed import ZedCollector
```

#### Return list ordering (lines 57–69):
```python
return [
    ...
    VSCodeCollector(),
    CursorCollector(),
    ChromeCollector(),
    FirefoxCollector(),
]
```
**Insert `ZedCollector()` after `CursorCollector()` and before `ChromeCollector()`:**
```python
    VSCodeCollector(),
    CursorCollector(),
    ZedCollector(),       # yields 1 section: Zed Extensions
    ChromeCollector(),
    FirefoxCollector(),
```
**Also update the docstring section count** (currently says "17 sections from 12 collectors") and the numbered list.

#### CodexCollector comment update (line 63):
```python
CodexCollector(),       # yields 1 section: MCP Servers
```
**Change to:**
```python
CodexCollector(),       # yields 2 sections: MCP Servers, Plugins
```

---

### `tests/collectors/test_codex.py` (MODIFY — add Plugins section tests)

**Analog:** existing `tests/collectors/test_codex.py` (all existing test classes)

#### Module-level import pattern (lines 1–20):
```python
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import maccat.collectors.codex as codex_mod
from maccat.collectors.codex import CodexCollector

SECRET_PATTERN = re.compile(r"token|Bearer|sk-|ghp_|key=|Authorization", re.IGNORECASE)
```
**No change needed — add new test classes to the same file.**

#### Test class structure (from `TestCodexDegradation` lines 210–251):
```python
class TestCodexDegradation:
    def test_codex_and_toml_both_absent_returns_empty(self, tmp_path: Path) -> None:
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].items == []
```
**New test class pattern for plugins:**
```python
class TestCodexPluginsSection:
    """Tests for CodexCollector._collect_plugins() — second section (CDX-02)."""

    def test_plugins_section_absent_both_paths(self, tmp_path: Path) -> None:
        """No CLI and no plugins in TOML → plugins section items == [] ('(none found)')."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[mcp_servers.some-srv]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        assert len(result.sections) == 2
        plugins_section = result.sections[1]
        assert plugins_section.title == "Codex Plugins"
        assert plugins_section.items == []
```

#### Section count assertion pattern (from `TestCodexDegradation.test_collect_returns_exactly_one_section` lines 243–251):
```python
def test_collect_returns_exactly_one_section(self, tmp_path: Path) -> None:
    ...
    assert len(result.sections) == 1
```
**Update** this existing test to assert `len(result.sections) == 2`.

#### monkeypatch of module-level path (from `test_cli_empty_array_falls_through_to_toml` lines 46–61):
```python
patch.object(codex_mod, "_TOML_PATH", config_toml)
```
**For plugins-specific TOML path constant:** if `_PLUGINS_TOML_PATH` is a separate module-level constant, patch it via `patch.object(codex_mod, "_PLUGINS_TOML_PATH", config_toml)`.

---

### `tests/collectors/test_zed.py` (CREATE)

**Analog:** `tests/collectors/test_firefox.py` (single-section JSON collector, monkeypatched module constant)

#### File header pattern (from `test_firefox.py` lines 1–14):
```python
"""Tests for maccat.collectors.firefox.

Behavioral spec: update-list.sh lines 2154–2206 (collect_firefox_extensions).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401

import maccat.collectors.firefox as ff_mod
from maccat.collectors.firefox import FirefoxCollector
```
**For `test_zed.py`:**
```python
"""Tests for maccat.collectors.zed.

Behavioral spec: Phase 27 CDX-02 / BRW-03 — Zed Extensions from index.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import maccat.collectors.zed as zed_mod
from maccat.collectors.zed import ZedCollector
```

#### Module-constant monkeypatch for path (from `test_firefox.py` line 70):
```python
with patch.object(ff_mod, "_FF_DIR", ff_dir):
    result = FirefoxCollector().collect()
```
**For Zed:** `patch.object(zed_mod, "_INDEX", tmp_index_path)`.

#### Absent-file degradation test pattern (from `test_firefox.py` lines 75–86):
```python
def test_firefox_section_title(self, tmp_path: Path) -> None:
    ff_dir = tmp_path / "Firefox"
    ff_dir.mkdir()
    # No profiles.ini — degraded path returns 1 empty section
    with patch.object(ff_mod, "_FF_DIR", ff_dir):
        result = FirefoxCollector().collect()
    assert result.sections[0].title == "Firefox Extensions"
```
**For Zed:**
```python
def test_zed_absent_index_returns_empty(self, tmp_path: Path) -> None:
    missing = tmp_path / "index.json"
    with patch.object(zed_mod, "_INDEX", missing):
        result = ZedCollector().collect()
    assert len(result.sections) == 1
    assert result.sections[0].title == "Zed Extensions"
    assert result.sections[0].items == []
```

#### Malformed JSON test (from `test_codex.py` `test_cli_malformed_json_returns_empty` lines 90–102):
```python
mock_r.stdout = "{not: json}"
...
result = CodexCollector().collect()
assert result.sections[0].items == []
```
**For Zed:**
```python
def test_zed_malformed_index_returns_empty(self, tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text("{not: valid json", encoding="utf-8")
    with patch.object(zed_mod, "_INDEX", index):
        result = ZedCollector().collect()
    assert result.sections[0].items == []
```

#### dev-filter test (no direct analog — use the `app-profile` filter pattern from `firefox.py`):
The Firefox location filter (`addon.get("location") != "app-profile"`) establishes the pattern for item-level filtering. Zed's dev filter mirrors it:
```python
def test_zed_excludes_dev_extensions(self, tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text(json.dumps({
        "extensions": {
            "html": {"manifest": {"name": "HTML", "version": "0.3.1"}, "dev": False},
            "my-local": {"manifest": {"name": "Local Dev", "version": "0.1.0"}, "dev": True},
        }
    }), encoding="utf-8")
    with patch.object(zed_mod, "_INDEX", index):
        result = ZedCollector().collect()
    items = result.sections[0].items
    assert any("HTML" in i for i in items)
    assert not any("Local Dev" in i for i in items)
```

#### Missing fields graceful degradation (from `test_firefox.py` non-dict addon handling + `test_codex.py` `test_cli_non_dict_array_element_degrades`):
```python
def test_zed_missing_manifest_fields_degrade(self, tmp_path: Path) -> None:
    """Entry with missing name/version fields degrades — uses ext_id as name fallback."""
    index = tmp_path / "index.json"
    index.write_text(json.dumps({
        "extensions": {
            "bare-id": {},   # no manifest key
        }
    }), encoding="utf-8")
    with patch.object(zed_mod, "_INDEX", index):
        result = ZedCollector().collect()  # must not raise
    items = result.sections[0].items
    assert any("bare-id" in i for i in items)
```

---

### Section-title uniqueness test (CREATE — new file in `tests/collectors/` or `tests/`)

**Analog:** no direct analog — this is a new test type. Closest structural pattern is the multi-collector import style from `test_codex.py` and `test_claude.py`.

#### Import pattern to collect all titles (from TITLE grep results — all 17+ constants):
Titles exist as:
- Module-level `_TITLE` (codex, firefox, chrome) — accessed as `module._TITLE`
- Module-level `TITLE` (mas, homebrew, setapp, webapps) — accessed as `module.TITLE`
- Class-level `TITLE` (vscode, cursor, setapp) — accessed as `ClassName.TITLE`
- Class-level `_PLUGINS_TITLE`, `_MCP_TITLE`, `_SKILLS_TITLE` (claude) — accessed as `ClaudeCollector._PLUGINS_TITLE` etc.
- Module-level `_EXT_TITLE`, `_MCP_TITLE` (gemini) — accessed as `gemini_mod._EXT_TITLE` etc.

**Test pattern (use direct module imports, collect into a list, assert no duplicates):**
```python
"""Assert all collector _TITLE / TITLE constants are unique (no copy-paste routing bugs)."""
from __future__ import annotations

import maccat.collectors.chrome as chrome_mod
import maccat.collectors.claude as claude_mod
import maccat.collectors.codex as codex_mod
import maccat.collectors.cursor as cursor_mod
import maccat.collectors.firefox as ff_mod
import maccat.collectors.gemini as gemini_mod
import maccat.collectors.homebrew as hb_mod
import maccat.collectors.mas as mas_mod
import maccat.collectors.opencode as oc_mod
import maccat.collectors.setapp as setapp_mod
import maccat.collectors.vscode as vscode_mod
import maccat.collectors.webapps as webapps_mod
import maccat.collectors.zed as zed_mod
from maccat.collectors.claude import ClaudeCollector
from maccat.collectors.cursor import CursorCollector
from maccat.collectors.opencode import OpenCodeCollector
from maccat.collectors.vscode import VSCodeCollector


def test_all_section_titles_are_unique() -> None:
    """All collector title constants must be unique — prevents reinstall routing bugs."""
    titles = [
        hb_mod.TITLE,
        mas_mod.TITLE,
        setapp_mod.TITLE,
        webapps_mod.TITLE,
        ClaudeCollector._PLUGINS_TITLE,
        ClaudeCollector._MCP_TITLE,
        ClaudeCollector._SKILLS_TITLE,
        codex_mod._TITLE,
        # new in Phase 27:
        codex_mod._PLUGINS_TITLE,
        # opencode — use module-level constants once confirmed naming
        OpenCodeCollector._PLUGINS_TITLE,   # or oc_mod._PLUGINS_TITLE depending on implementation
        ...
        zed_mod._TITLE,
        chrome_mod._TITLE,
        ff_mod._TITLE,
    ]
    assert len(titles) == len(set(titles)), (
        f"Duplicate section titles found: {[t for t in titles if titles.count(t) > 1]}"
    )
```
**Note:** `opencode.py` and `gemini.py` use module-level `_PLUGINS_TITLE`/`_MCP_TITLE`/`_AGENTS_TITLE`/`_EXT_TITLE` — confirm exact constant names before writing the test. The pattern is: read the module, use `module_mod._CONST_NAME` for module-level constants or `ClassName._ATTR` for class-level.

---

## Shared Patterns

### `from __future__ import annotations` — line 1 of every file
**Source:** all existing collectors (e.g. `claude.py` line 7, `codex.py` line 7, `firefox.py` line 7)
**Apply to:** `zed.py`, any new test files

### Module-level constants for monkeypatching
**Source:** `codex.py` lines 18–24, `firefox.py` lines 16–17
**Rule:** path/title constants MUST be module-level (not inside class body) so tests can use `patch.object(module, "CONSTANT_NAME", value)`. This is the project-wide test-isolation contract.
```python
# Correct — patchable
_INDEX = Path.home() / "Library/Application Support/Zed/extensions/index.json"
_TITLE = "Zed Extensions"

# Wrong — not patchable without class-attribute lookup
class ZedCollector(Collector):
    _INDEX = Path.home() / ...
```
**Exception:** `claude.py` uses class-level `_PLUGINS_TITLE` etc. (titles only, not paths). Paths are always module-level.

### Never-raising collect() contract
**Source:** `codex.py` lines 44–77, `firefox.py` lines 51–55
**Rule:** every `collect()` and sub-collector wraps file reads and subprocess calls in `try/except (json.JSONDecodeError, OSError)`, returns `[]` or empty `Section` on any error.

### `emit_item(name, version, id_)` call discipline
**Source:** `format.py` lines 16–43
**FMT-03 for codex plugins:** version is always `""` (no version available from identity-only sources). `emit_item(name, "", id_)` → `"name [id]"` per the name+id branch at line 38.

### `(none found)` via empty items list
**Source:** `format.py` `flush_section` lines 46–73
**Rule:** collectors never write `"(none found)"` directly — they return `items=[]` and the orchestrator calls `flush_section([])` which produces `["  (none found)"]`. All new sections use `raw=False` (the default).

### CAT-05 TOML-header-only discipline
**Source:** `codex.py` lines 79–99 + docstring lines 82–84
**Rule for `_collect_plugins` TOML path:** use `re.match()` on each line to extract the section header key; never call `tomllib.loads()` on the file; never read value lines. Mirrors the existing `_collect_via_toml` exactly, changing only the regex pattern.

---

## No Analog Found

All files have analogs. No new patterns without prior examples.

---

## Metadata

**Analog search scope:** `src/maccat/collectors/`, `src/maccat/catalog/`, `src/maccat/helpers/`, `tests/collectors/`
**Files read:** `codex.py`, `claude.py`, `firefox.py`, `__init__.py`, `base.py`, `format.py`, `json_io.py`, `test_codex.py`, `test_cursor.py`, `test_firefox.py`, `test_claude.py`
**Pattern extraction date:** 2026-06-17
