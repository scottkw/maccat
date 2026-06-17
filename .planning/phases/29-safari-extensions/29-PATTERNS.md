# Phase 29: Safari Extensions - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 5 (2 create, 2 modify, 1 modify-test)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/maccat/collectors/safari.py` | collector | subprocess + file-I/O (plist) | `src/maccat/collectors/codex.py` + `src/maccat/helpers/plist_version.py` | role-match (subprocess+plist chain) |
| `src/maccat/collectors/__init__.py` | registry | config | `src/maccat/collectors/__init__.py` (itself, Firefox tail) | exact |
| `tests/collectors/test_safari.py` | test | — | `tests/collectors/test_codex.py` + `tests/test_pyz.py` | role-match |
| `tests/collectors/test_section_titles.py` | test | — | itself (current file) | exact |

---

## Pattern Assignments

### `src/maccat/collectors/safari.py` (collector, subprocess + plist file-I/O)

**Primary analog:** `src/maccat/collectors/codex.py`
**Secondary analog:** `src/maccat/helpers/plist_version.py`
**Tertiary analog (NOTE + raw=False pattern):** `src/maccat/collectors/firefox.py`

---

**Imports pattern** — copy from `codex.py` lines 1–18, adapt for plistlib/re:

```python
from __future__ import annotations

import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.plist_version import get_plist_version
```

**Module-level constants** — copy module-constant discipline from `codex.py` lines 25–27 (comment explains why NOT inside class — enables monkeypatching):

```python
# ---------------------------------------------------------------------------
# Module-level constants — NOT inside class so tests can monkeypatch via
# patch.object(safari_mod, "_PLUGINKIT", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_TITLE = "Safari Extensions"
_PLUGINKIT = Path("/usr/bin/pluginkit")
_PLUGIN_POINT = "com.apple.Safari.web-extension"
```

---

**Availability / NOTE pattern** — copy from `firefox.py` lines 80–85 (NOTE to stderr, return empty section):

```python
# firefox.py lines 80-85
def collect(self) -> CollectorResult:
    profiles_ini = _FF_DIR / "profiles.ini"
    if not profiles_ini.is_file():
        print("  NOTE: Firefox not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```

For SafariCollector adapt to: `if not _PLUGINKIT.is_file():` then NOTE + empty section.

---

**Subprocess try/except OSError pattern** — copy from `mas.py` lines 75–91 (the canonical never-raising subprocess block):

```python
# mas.py lines 75-91
try:
    result = subprocess.run(
        ["mas", "list"], capture_output=True, text=True, shell=False
    )
except OSError as exc:
    # TOCTOU / broken symlink / exec failure: warn-and-continue per the
    # project's graceful-degradation constraint instead of crashing the CLI.
    print(f"  WARNING: could not run mas: {exc}", file=sys.stderr)
    return CollectorResult(
        sections=[
            Section(
                title=TITLE,
                items=["Could not retrieve App Store list."],
                raw=True,
            )
        ]
    )
if result.returncode != 0:
    print(
        f"  WARNING: mas list failed (exit {result.returncode}).",
        file=sys.stderr,
    )
    return CollectorResult(...)
```

For SafariCollector: same structure, `shell=False`, wrap `subprocess.run(["pluginkit", "-mAvv", "-p", _PLUGIN_POINT], ...)`. On non-zero exit OR empty stdout, return `CollectorResult(sections=[Section(title=_TITLE, items=[])])` (no error message in items — raw=False, flush_section produces `(none found)`).

---

**plist version reuse** — `src/maccat/helpers/plist_version.py` lines 24–64 — import and call directly, do NOT reimplement:

```python
# helpers/plist_version.py lines 40-50 — the never-raising pattern to reuse
try:
    if not path.is_file() or path.stat().st_size == 0:
        return ""
    with path.open("rb") as fh:
        data = plistlib.load(fh)
except Exception:  # noqa: BLE001
    return ""
```

For name + id reads, write a Safari-local helper `_read_appex_plist(appex_path: Path) -> dict[str, str]` that follows the same never-raising structure (same broad `except Exception` with `# noqa: BLE001`) but returns `{"name": ..., "id": ...}` — single `plistlib.load` call with key precedence applied inline.

---

**Per-extension individual try/except** — key pattern: each extension plist read is wrapped in its OWN try/except, not a single outer block. Modeled on `plist_version.py`'s approach but applied per-loop-iteration:

```python
# Pattern: individual never-raising per-extension block
items: list[str] = []
for appex_path in appex_paths:
    try:
        info_plist = appex_path / "Contents" / "Info.plist"
        # ... plistlib.load, name/version/id extraction ...
        line = emit_item(name, version, id_)
        if line:
            items.append(line)
    except Exception:  # noqa: BLE001
        continue       # single bad plist never aborts the whole collection
```

---

**emit_item + raw=False (flush_section)** — copy from `firefox.py` line 93:

```python
# firefox.py line 93
return CollectorResult(sections=[Section(title=_TITLE, items=all_items)])
# raw defaults to False — flush_section handles sort + dedup + (none found)
```

SafariCollector uses the same: `Section(title=_TITLE, items=items)` with no `raw=True`.

---

**Name resolution chain** — Safari-specific, no direct analog in codebase. Implement inline in `_read_appex_plist`:

```
plist["CFBundleDisplayName"]              # primary
  → parent_app_plist["CFBundleDisplayName"] # three levels up: ../../..
  → parent_app_plist["CFBundleName"]      # only if not "safari" (generic binary name)
  → bundle_id (from pluginkit output line)  # final fallback — never empty
```

The "never `CFBundleName` when it equals `'safari'`" guard is Safari-specific. No analog — implement per CONTEXT.md §Entry fields.

---

**pluginkit output parse** — parse `_parse_pluginkit_output(stdout: str) -> list[Path]` using regex per CONTEXT.md §pluginkit invocation. No direct analog. Use the regex:

```python
_PATH_RE = re.compile(r"^\s*Path\s*=\s*(.+\.appex)\s*$")

def _parse_pluginkit_output(stdout: str) -> list[Path]:
    paths: list[Path] = []
    for line in stdout.splitlines():
        m = _PATH_RE.match(line)
        if m:
            paths.append(Path(m.group(1).strip()))
    return paths
```

This is a module-level constant (`_PATH_RE`) following the `codex.py` module-constant discipline so tests can inspect it.

---

### `src/maccat/collectors/__init__.py` (registry, config)

**Analog:** itself — current file lines 1–80.

**Current tail of get_registry()** (lines 64–80 — the Firefox position to insert after):

```python
# __init__.py lines 64-80 (current)
    return [
        HomebrewCollector(),
        MasCollector(),
        ...
        ZedCollector(),         # yields 1 section: Zed Extensions
        ChromeCollector(),
        EdgeCollector(),        # NEW — BRW-01
        BraveCollector(),       # NEW — BRW-02
        FirefoxCollector(),
    ]
```

**Change required:** Add `SafariCollector` import (deferred inside function body, same pattern as all other imports at lines 46–60) and append `SafariCollector()` AFTER `FirefoxCollector()`. Also update the docstring section count from 21 → 22 and add entry `22. Safari Extensions`.

**Import pattern to follow** (lines 46–60 — all deferred, alphabetical by module name, inside function body):

```python
    from maccat.collectors.safari import SafariCollector
```

---

### `tests/collectors/test_safari.py` (test, new)

**Primary analog:** `tests/collectors/test_codex.py`
**Secondary analog:** `tests/test_pyz.py` (live-gated skip pattern)
**Tertiary analog:** `tests/collectors/test_zed.py` (patch.object monkeypatch pattern)

---

**File header + imports pattern** — copy from `test_codex.py` lines 1–13:

```python
"""Tests for maccat.collectors.safari.

Behavioral spec: Phase 29 BRW-04 — Safari Extensions via pluginkit + plistlib.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import maccat.collectors.safari as safari_mod
from maccat.collectors.safari import SafariCollector
```

**Live-gated skip pattern** — copy from `test_pyz.py` lines 27–31:

```python
# test_pyz.py lines 27-31
def _require_pyz() -> None:
    """Skip the calling test if dist/maccat.pyz has not been built."""
    if not PYZ.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")
```

For SafariCollector adapt to:

```python
def _require_pluginkit() -> None:
    """Skip the calling test if /usr/bin/pluginkit is not present (keeps CI green)."""
    if not Path("/usr/bin/pluginkit").exists():
        pytest.skip("/usr/bin/pluginkit not present on this machine")
```

**patch.object monkeypatch pattern** — copy from `test_zed.py` lines 25–26 and `test_codex.py` lines 53–57:

```python
# test_zed.py — monkeypatching a module-level Path constant
with patch.object(zed_mod, "_INDEX", missing):
    result = ZedCollector().collect()

# test_codex.py — monkeypatching _TOML_PATH
with patch.object(codex_mod, "_TOML_PATH", config_toml):
    result = CodexCollector().collect()
```

For SafariCollector: `patch.object(safari_mod, "_PLUGINKIT", tmp_path / "no-pluginkit")` to simulate absent pluginkit.

**subprocess.run mock pattern** — copy from `test_codex.py` lines 33–43:

```python
# test_codex.py lines 33-43
mock_r = MagicMock()
mock_r.returncode = 0
mock_r.stdout = json.dumps([{"name": "s1", "type": "stdio"}])
with (
    patch("shutil.which", return_value="/usr/bin/codex"),
    patch("subprocess.run", return_value=mock_r),
):
    result = CodexCollector().collect()
```

For SafariCollector: `mock_r.stdout = BITWARDEN_FIXTURE` (the verbatim pluginkit output from CONTEXT.md §Specific Ideas). No `shutil.which` needed — SafariCollector checks `_PLUGINKIT.is_file()`, not `shutil.which`. Use `patch.object(safari_mod, "_PLUGINKIT", real_pluginkit_path)` + `patch("subprocess.run", return_value=mock_r)`.

**Test class structure** — mirror `test_codex.py` class groupings:

```
TestSafariParsePluginkitOutput   # unit-tests _parse_pluginkit_output with fixture string
TestSafariCollect                # full collect() with mocked subprocess + tmp plist files
TestSafariDegradation            # pluginkit absent, non-zero exit, empty output, bad plist
TestSafariNameResolution         # CFBundleDisplayName vs CFBundleName fallback chain
TestSafariSmoke                  # live-gated: calls real pluginkit, asserts no exception
```

**section title + raw=False assertions** — copy from `test_codex.py` lines 253–271:

```python
# test_codex.py lines 253-271
def test_codex_section_title(...):
    assert result.sections[0].title == "Codex MCP Servers"

def test_codex_raw_is_false(...):
    assert result.sections[0].raw is False
```

---

### `tests/collectors/test_section_titles.py` (modify existing)

**Analog:** itself — current file.

**Count assertion to bump** (line 83):

```python
# Current (line 83)
assert len(titles) == 21, f"Expected 21 titles, got {len(titles)}"

# After change
assert len(titles) == 22, f"Expected 22 titles, got {len(titles)}"
```

**Import to add** (follow alphabetical pattern in lines 10–28):

```python
import maccat.collectors.safari as safari_mod
```

**Title constant to add to `titles` list** (lines 60–82, after `ff_mod._TITLE`):

```python
safari_mod._TITLE,               # "Safari Extensions"
```

**Docstring update** — bump "21 collector section title constants" → "22" and add the Safari entry to the comment block listing title locations.

---

## Shared Patterns

### Never-raising subprocess block
**Source:** `src/maccat/collectors/mas.py` lines 75–107
**Apply to:** `safari.py` outer pluginkit call
```python
try:
    result = subprocess.run([...], capture_output=True, text=True, shell=False)
except OSError as exc:
    print(f"  WARNING: could not run ...: {exc}", file=sys.stderr)
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
if result.returncode != 0:
    print(f"  WARNING: ... failed (exit {result.returncode}).", file=sys.stderr)
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```

### Never-raising plist read
**Source:** `src/maccat/helpers/plist_version.py` lines 40–50
**Apply to:** `safari.py` per-extension plist reads (name + id helper AND the `get_plist_version` call for version)
```python
try:
    if not path.is_file() or path.stat().st_size == 0:
        return ""
    with path.open("rb") as fh:
        data = plistlib.load(fh)
except Exception:  # noqa: BLE001
    return ""
```

### Module-level constants (monkeypatch discipline)
**Source:** `src/maccat/collectors/codex.py` lines 23–27, `src/maccat/collectors/zed.py` lines 15–19
**Apply to:** `safari.py` — `_TITLE`, `_PLUGINKIT`, `_PLUGIN_POINT` must be module-level, NOT class attributes
```python
# codex.py lines 23-27 comment:
# Module-level constants — NOT inside class so tests can monkeypatch via
# patch.object(codex_mod, "_TOML_PATH", ...) without class-attribute lookup.
```

### NOTE to stderr when not installed
**Source:** `src/maccat/collectors/firefox.py` lines 83–85, `src/maccat/collectors/zed.py` lines 39–40
**Apply to:** `safari.py` when `_PLUGINKIT.is_file()` is False
```python
print("  NOTE: Firefox not installed.", file=sys.stderr)
# or:
print("  NOTE: Zed not installed.", file=sys.stderr)
```

### raw=False (flush_section path)
**Source:** `src/maccat/collectors/firefox.py` line 93, `src/maccat/collectors/zed.py` line 70
**Apply to:** `safari.py` — `Section(title=_TITLE, items=items)` with no `raw=True` kwarg; orchestrator calls `flush_section` which produces sort + dedup + `(none found)` when items is empty.

### `from __future__ import annotations` line 1
**Source:** Every collector file — `codex.py` line 9, `zed.py` line 1, `firefox.py` line 1, `mas.py` line 2
**Apply to:** `safari.py` line 1, `test_safari.py` line 1

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `_parse_pluginkit_output()` helper | utility | text parsing | No other collector parses `pluginkit` verbose output; regex + tab-separated line parse is novel for this codebase |
| `_read_appex_plist()` helper | utility | plist file-I/O | `get_plist_version` covers version only; name/id multi-key resolution with `CFBundleDisplayName` fallback chain is Safari-specific |

Both should be implemented as module-level private functions in `safari.py` (not methods), following the same `plist_version.py` never-raising `except Exception: # noqa: BLE001` discipline.

---

## Key Fixture (embed verbatim in test_safari.py)

From CONTEXT.md §Specific Ideas — live-verified Bitwarden output:

```
_BITWARDEN_FIXTURE = """\
     com.bitwarden.desktop.safari(2026.5.0)
            Path = /Applications/Bitwarden.app/Contents/PlugIns/safari.appex
            UUID = 5AFDA995-8D64-43CA-B696-154F57ABF85B
       Timestamp = 2026-06-08 02:49:27 +0000
             SDK = com.apple.Safari.web-extension
   Parent Bundle = /Applications/Bitwarden.app
"""
```

This is the fixture for `TestSafariParsePluginkitOutput.test_parse_extracts_appex_path` — assert `_parse_pluginkit_output(_BITWARDEN_FIXTURE)` returns `[Path("/Applications/Bitwarden.app/Contents/PlugIns/safari.appex")]`.

---

## Metadata

**Analog search scope:** `src/maccat/collectors/`, `src/maccat/helpers/`, `tests/collectors/`, `tests/test_pyz.py`
**Files scanned:** 10 source files read in full
**Pattern extraction date:** 2026-06-17
