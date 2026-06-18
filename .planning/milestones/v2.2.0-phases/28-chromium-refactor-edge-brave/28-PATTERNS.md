# Phase 28: Chromium Refactor + Edge + Brave - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 7 (4 create, 3 modify)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/maccat/collectors/chromium.py` | base-class | file-I/O (manifest scan) | `src/maccat/collectors/chrome.py` | exact — move verbatim |
| `src/maccat/collectors/chrome.py` | collector/thin-subclass | file-I/O | `src/maccat/collectors/cursor.py` | exact — thin-subclass pattern |
| `src/maccat/collectors/edge.py` | collector/thin-subclass | file-I/O | `src/maccat/collectors/chrome.py` (post-refactor) | exact — same shape |
| `src/maccat/collectors/brave.py` | collector/thin-subclass | file-I/O | `src/maccat/collectors/chrome.py` (post-refactor) | exact — same shape |
| `src/maccat/collectors/__init__.py` | registry/config | — | `src/maccat/collectors/__init__.py` (current) | self — incremental add |
| `tests/collectors/test_chrome.py` | test (modify) | — | `tests/collectors/test_chrome.py` (current) | self — patch target change only |
| `tests/collectors/test_edge.py` + `test_brave.py` | test (create) | — | `tests/collectors/test_chrome.py` | exact — mirror structure |
| `tests/collectors/test_section_titles.py` | test (modify) | — | `tests/collectors/test_section_titles.py` (current) | self — count bump + 2 entries |

---

## Pattern Assignments

### `src/maccat/collectors/chromium.py` (new base class)

**Analog:** `src/maccat/collectors/chrome.py` (full file — move logic verbatim)

**Imports pattern** (chrome.py lines 1–13 — copy as-is, rename `__all__`):
```python
from __future__ import annotations

import sys
from pathlib import Path

from maccat.catalog.format import emit_item, version_sort_tail
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.chrome_name import chrome_ext_name
from maccat.helpers.json_io import json_get

__all__ = ["ChromiumBaseCollector", "COMPONENT_DENYLIST"]
```

**COMPONENT_DENYLIST** (chrome.py lines 17–30 — move here verbatim):
```python
# Component extensions pre-installed by Chrome — excluded from output.
# Source: update-list.sh:2078–2087 (denylist of 10 IDs — never a file, never an env var).
COMPONENT_DENYLIST: frozenset[str] = frozenset({
    "nmmhkkegccagdldgiimedpiccmgmieda",
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi",
    "aapocclcgogkmnckojhhkbfbldkacnbeo",
    "blpcfgokakmgnkcojhhkbfbldkacnbeo",
    "felcaaldnbdncclmgdcncolpebgiejap",
    "aohghmighlieiainnegkcijnfilokake",
    "apdfllckaahabafndbhieahigkjlhalf",
    "pjkljhegncpnkpknbcohdijeoejaedia",
    "mhjfbmdgcfjbbpaeojofohoefgiehjai",
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm",
})
```

**Class-attribute parameterization pattern** (new — no existing analog; use ARCHITECTURE.md):
```python
class ChromiumBaseCollector(Collector):
    """Shared Chromium extension scan, parameterized by browser name and base path.

    Subclasses override _base, _title, and _denylist only.
    """

    _base: Path = Path()
    _title: str = ""
    _denylist: frozenset[str] = frozenset()
```

**Core collect() pattern** (chrome.py lines 84–103 — move verbatim, replace `_BASE` with `self._base`, `_TITLE` with `self._title`, `COMPONENT_DENYLIST` with `self._denylist`):
```python
def collect(self) -> CollectorResult:
    """Enumerate all Chrome profiles and collect installed extensions."""
    if not _BASE.is_dir():                          # → self._base.is_dir()
        print("  NOTE: Google Chrome not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=_TITLE, items=[])])

    all_items: list[str] = []

    # Profile enumeration: Default first, then sorted "Profile *" dirs (zsh :2089)
    profile_dirs: list[Path] = [_BASE / "Default"]     # → self._base / "Default"
    profile_dirs += sorted(_BASE.glob("Profile */"))   # → self._base.glob(...)

    for profile in profile_dirs:
        ext_root = profile / "Extensions"
        if not ext_root.is_dir():
            continue
        all_items.extend(self._collect_profile(ext_root))

    # raw=False: Phase 16 orchestrator calls flush_section for cross-profile dedup
    return CollectorResult(sections=[Section(title=_TITLE, items=all_items)])
                                                       # → self._title
```

**CRITICAL — presence detection rule** (from CONTEXT.md): The NOTE message fires only when `self._base` does not exist at all. When `self._base` exists but contains only `NativeMessagingHosts` (Brave false-positive case), the profile enumeration loop naturally produces zero `ext_root.is_dir()` hits → `all_items` stays `[]` → no NOTE, no spurious section content. Do NOT add an extra `is_dir()` guard before the loop.

**_collect_profile() pattern** (chrome.py lines 50–82 — move verbatim, replace `COMPONENT_DENYLIST` with `self._denylist`):
```python
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
        if ext_id == "Temp" or ext_id.startswith("_") or ext_id in COMPONENT_DENYLIST:
            continue                                    # → self._denylist
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
```

---

### `src/maccat/collectors/chrome.py` (thin subclass after refactor)

**Analog:** `src/maccat/collectors/cursor.py` (thin-subclass pattern; lines 1–31)

**What stays vs what moves:**
- **Moves to chromium.py:** `COMPONENT_DENYLIST`, `_collect_profile`, `collect()`, imports for `emit_item`, `version_sort_tail`, `chrome_ext_name`, `json_get`
- **Stays in chrome.py:** Module docstring, `_BASE` module constant, `ChromeCollector` thin subclass (3 class attrs), `__all__` re-export

**Post-refactor chrome.py** (full file — ~18 lines):
```python
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["ChromeCollector", "COMPONENT_DENYLIST"]  # re-export for backward compat

_BASE = Path.home() / "Library/Application Support/Google/Chrome"


class ChromeCollector(ChromiumBaseCollector):
    """Thin subclass — Chrome-specific paths and denylist only."""

    _base = _BASE
    _title = "Google Chrome Extensions"
    _denylist = COMPONENT_DENYLIST
```

**Re-export is mandatory.** `test_chrome.py` line 14 imports `from maccat.collectors.chrome import COMPONENT_DENYLIST`. Without the re-export, this raises `ImportError`. The `__all__` entry is also required for mypy `--strict`.

**`_BASE` module constant must remain in chrome.py.** Tests that use `patch.object(chrome_mod, "_BASE", ...)` (old pattern) rely on module-level `_BASE`. After refactor the correct patch is `patch.object(ChromeCollector, "_base", new=tmp_path)` — but keeping `_BASE` at module level in chrome.py preserves module-import compatibility. See test_chrome.py pattern below.

---

### `src/maccat/collectors/edge.py` (new thin subclass)

**Analog:** `src/maccat/collectors/chrome.py` post-refactor (same shape)

**Full file pattern:**
```python
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["EdgeCollector", "EDGE_COMPONENT_DENYLIST"]

# Edge-specific component extension IDs.
# NOTE: Microsoft publishes no canonical component-ID list. This constant uses the
# Chrome baseline as a starting point. Expand it by installing Edge, opening
# edge://extensions, and cross-referencing IDs on disk in Default/Extensions/ that
# are invisible in the extensions UI (those are component IDs). Do not block the
# phase on completeness — over-listing user extensions is the failure mode.
EDGE_COMPONENT_DENYLIST: frozenset[str] = frozenset()  # populated during implementation

_BASE = Path.home() / "Library/Application Support/Microsoft Edge"


class EdgeCollector(ChromiumBaseCollector):
    """Thin subclass — Edge-specific paths and denylist."""

    _base = _BASE
    _title = "Microsoft Edge Extensions"
    _denylist = COMPONENT_DENYLIST | EDGE_COMPONENT_DENYLIST
```

---

### `src/maccat/collectors/brave.py` (new thin subclass)

**Analog:** `src/maccat/collectors/chrome.py` post-refactor (same shape)

**Full file pattern:**
```python
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["BraveCollector", "BRAVE_COMPONENT_DENYLIST"]

# Brave-specific component extension IDs.
# Source: https://github.com/brave/brave-browser/wiki/Brave-Components
# 20 confirmed IDs (32-char lowercase alpha) — fully verified from wiki.
BRAVE_COMPONENT_DENYLIST: frozenset[str] = frozenset({
    # Populate from STACK.md / Brave Components wiki — 20 IDs total
    # Planner: look up the 20 IDs from STACK.md during implementation
})

_BASE = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"


class BraveCollector(ChromiumBaseCollector):
    """Thin subclass — Brave-specific paths and denylist."""

    _base = _BASE
    _title = "Brave Browser Extensions"
    _denylist = COMPONENT_DENYLIST | BRAVE_COMPONENT_DENYLIST
```

**NOTE on `_title`:** CONTEXT.md line 49 specifies `"Brave Browser Extensions"` as the section title. Confirm this is what the user wants — ARCHITECTURE.md section titles say `"Brave Extensions"` (shorter form). CONTEXT.md decisions are locked; use `"Brave Browser Extensions"`.

---

### `src/maccat/collectors/__init__.py` (modify — add Edge + Brave)

**Analog:** Current file (self-reference — incremental add)

**Current Chrome→Firefox block** (lines 44, 72–74):
```python
    from maccat.collectors.chrome import ChromeCollector
    from maccat.collectors.firefox import FirefoxCollector
    ...
        ChromeCollector(),
        FirefoxCollector(),
```

**Post-phase Chrome→Edge→Brave→Firefox block:**
```python
    from maccat.collectors.brave import BraveCollector
    from maccat.collectors.chrome import ChromeCollector
    from maccat.collectors.edge import EdgeCollector
    from maccat.collectors.firefox import FirefoxCollector
    ...
        ChromeCollector(),
        EdgeCollector(),   # NEW
        BraveCollector(),  # NEW
        FirefoxCollector(),
```

**Section count in docstring:** Update from `19 sections from 13 collectors` to `21 sections from 15 collectors`. Add lines 19–20 to the docstring section list:
```
      19. Microsoft Edge Extensions
      20. Brave Browser Extensions
      21. Firefox Extensions       ← was 19
```

*(The docstring currently shows Google Chrome Extensions as section 18 and Firefox as 19; bump Firefox to 21, insert Edge at 19 and Brave at 20.)*

---

### `tests/collectors/test_chrome.py` (modify — patch target only)

**Analog:** Current file (self-reference)

**All 7 current `patch.object(chrome_mod, "_BASE", ...)` calls** (lines 43, 57, 67, 75, 95, 109, 118, 141, 160) must change to `patch.object(ChromeCollector, "_base", new=...)`.

**Before** (e.g. line 43):
```python
with patch.object(chrome_mod, "_BASE", base):
    result = ChromeCollector().collect()
```

**After:**
```python
with patch.object(ChromeCollector, "_base", new=base):
    result = ChromeCollector().collect()
```

**Why:** After refactor, `ChromeCollector._base = _BASE` is set at class-definition time. Patching the module constant `chrome_mod._BASE` afterwards does NOT retroactively update the class attribute. `patch.object(ChromeCollector, "_base", new=...)` patches the class attribute directly, which `self._base` reads at runtime.

**Import line 14 stays unchanged:** `from maccat.collectors.chrome import COMPONENT_DENYLIST, ChromeCollector` — chrome.py re-exports `COMPONENT_DENYLIST`, so this import continues to work.

---

### `tests/collectors/test_edge.py` + `tests/collectors/test_brave.py` (new)

**Analog:** `tests/collectors/test_chrome.py` (mirror structure exactly)

**Import block pattern** (mirror test_chrome.py lines 1–14, substituting module name):
```python
"""Tests for maccat.collectors.edge."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401

import maccat.collectors.edge as edge_mod
from maccat.collectors.edge import EDGE_COMPONENT_DENYLIST, EdgeCollector
```

**`_make_ext` helper** (test_chrome.py lines 21–28 — copy verbatim into each new test file, no changes needed):
```python
def _make_ext(profile_ext_dir: Path, ext_id: str, version: str, name: str) -> None:
    """Build a synthetic Chrome extension directory with a minimal manifest.json."""
    ver_dir = profile_ext_dir / ext_id / version
    ver_dir.mkdir(parents=True)
    (ver_dir / "manifest.json").write_text(
        json.dumps({"name": name, "version": version}),
        encoding="utf-8",
    )
```

**Patch pattern** (test_chrome.py post-update — use `patch.object(EdgeCollector, "_base", new=base)` not module-level constant):
```python
with patch.object(EdgeCollector, "_base", new=base):
    result = EdgeCollector().collect()
```

**Required test classes** (mirror test_chrome.py class structure):

| Test Class | Tests to include |
|---|---|
| `TestEdgeCollect` | `test_collects_default_profile`, `test_collects_multiple_profiles`, `test_edge_section_title` (assert `== "Microsoft Edge Extensions"`), `test_edge_raw_is_false` |
| `TestEdgeExclusions` | `test_skips_component_extension`, `test_skips_temp_directory`, `test_skips_underscore_directory`, `test_version_sort_tail_used` |
| `TestEdgeDegradation` | `test_edge_not_installed`, `test_profile_iterdir_oserror_degrades`, `test_ext_dir_iterdir_oserror_skips_that_ext` |
| `TestEdgeNativeMessagingOnly` | **NEW** — unique to Edge/Brave: base dir exists but has only `NativeMessagingHosts/`, no `Extensions/` dirs → `items == []`, NO NOTE to stderr (see presence detection rule above) |

**NativeMessagingHosts fixture test** (Brave false-positive guard — new pattern not in test_chrome.py):
```python
def test_base_dir_without_profiles_returns_empty_silently(
    self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Base dir exists (e.g. NativeMessagingHosts only) but no Extensions dirs.
    Must return items==[] with NO NOTE to stderr (presence detection via profile
    enumeration, not bare is_dir())."""
    base = tmp_path / "BraveSoftware" / "Brave-Browser"
    (base / "NativeMessagingHosts").mkdir(parents=True)
    with patch.object(BraveCollector, "_base", new=base):
        result = BraveCollector().collect()
    assert result.sections[0].items == []
    captured = capsys.readouterr()
    assert "NOTE" not in captured.err  # NO spurious note
```

*(Replicate for EdgeCollector with Edge's base dir path.)*

---

### `tests/collectors/test_section_titles.py` (modify — count + 2 new titles)

**Analog:** Current file (self-reference)

**Current state** (lines 29–80): 19 titles in a list, `assert len(titles) == 19`.

**Changes required:**

1. Add two new module imports at the top (after `import maccat.collectors.zed as zed_mod`):
```python
import maccat.collectors.brave as brave_mod
import maccat.collectors.edge as edge_mod
```

2. In `test_all_section_titles_are_unique()`, extend the `titles` list (after `chrome_mod._TITLE` and before `ff_mod._TITLE`):
```python
        edge_mod._TITLE,                 # "Microsoft Edge Extensions"
        brave_mod._TITLE,                # "Brave Browser Extensions"
```

3. Update the count assertion (line 77):
```python
    assert len(titles) == 21, f"Expected 21 titles, got {len(titles)}"
```

4. Update the docstring count from "19" to "21" and add the two new title lines to the `Title constant locations:` block:
```
      edge_mod._TITLE                — "Microsoft Edge Extensions"
      brave_mod._TITLE               — "Brave Browser Extensions"
```

**NOTE on title constant access:** `edge.py` and `brave.py` expose their titles as `_TITLE` module-level constants (same pattern as `chrome_mod._TITLE`, `ff_mod._TITLE`, `zed_mod._TITLE`). Do NOT use `EdgeCollector._title` (class attribute) — the uniqueness test consistently accesses module-level constants, not class attributes.

---

## Shared Patterns

### `from __future__ import annotations` — line 1 of every file
**Source:** All existing collector files (chrome.py line 5, firefox.py line 1, cursor.py line 1)
**Apply to:** `chromium.py`, `edge.py`, `brave.py` (all new files)

### NOTE-to-stderr on absent base dir
**Source:** `chrome.py` lines 87–88, `firefox.py` lines 84–85
```python
if not _BASE.is_dir():
    print("  NOTE: Google Chrome not installed.", file=sys.stderr)
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
```
**Apply to:** `ChromiumBaseCollector.collect()` (parameterize browser name from `self._title` or a `_browser_name` attr)

### `raw=False` default for extension collectors
**Source:** `chrome.py` line 102–103, `firefox.py` line 92–93
```python
# raw=False: Phase 16 orchestrator calls flush_section for cross-profile dedup
return CollectorResult(sections=[Section(title=_TITLE, items=all_items)])
```
**Apply to:** `ChromiumBaseCollector.collect()` — `Section` default `raw=False` is inherited; do not set `raw=True`

### OSError degradation in iterdir()
**Source:** `chrome.py` lines 54–57 (profile-level) and lines 67–69 (version-dir-level)
```python
try:
    ext_dirs = list(extensions_dir.iterdir())
except OSError:
    return items
```
**Apply to:** `ChromiumBaseCollector._collect_profile()` — copy both OSError guards verbatim

### `version_sort_tail` — MUST use, do not substitute
**Source:** `chrome.py` line 70, import line 10
```python
from maccat.catalog.format import emit_item, version_sort_tail
...
ver_dir = version_sort_tail(candidates)
```
**Apply to:** `ChromiumBaseCollector._collect_profile()` — do NOT use `max()`, `sorted()[-1]`, or `natsorted()`; byte-parity with update-list.sh requires `version_sort_tail`

### `patch.object(CollectorClass, "_base", new=tmp_path)` — test patch pattern
**Source:** test_chrome.py (post-update), test_cursor.py line 35
```python
with patch.object(CursorCollector, "_EXT_DIR", cursor_extensions):
    ...
```
**Apply to:** All new test files (`test_chrome.py` updated, `test_edge.py`, `test_brave.py`) — patch the class attribute directly, never the module constant

### Deferred imports inside `get_registry()`
**Source:** `collectors/__init__.py` lines 12–18 (function body imports)
```python
def get_registry() -> list[Collector]:
    from maccat.collectors.brave import BraveCollector
    from maccat.collectors.chrome import ChromeCollector
    ...
```
**Apply to:** `__init__.py` — new `BraveCollector` and `EdgeCollector` imports go inside `get_registry()` body, alphabetically with existing imports

---

## No Analog Found

All files have strong analogs. No new parsing logic or new helper modules are required for Phase 28.

---

## Key Constraints (copy into every plan action)

1. **`_collect_profile` uses `self._denylist`** — not the module-level `COMPONENT_DENYLIST` constant. The base class reads `self._denylist`; each subclass sets it as a class attribute.
2. **`_TITLE` must be a module-level constant** in each subclass file (`edge.py`, `brave.py`) — `test_section_titles.py` accesses `edge_mod._TITLE`, not `EdgeCollector._title`.
3. **Chrome output is byte-identical** — run `test_chrome.py` green (with updated patch targets) before committing chromium.py. This is the single most important regression check.
4. **NativeMessagingHosts-only base dir must produce items=[], no NOTE** — profile enumeration loop handles this; do NOT add an extra `is_dir()` check before the loop.
5. **`COMPONENT_DENYLIST` re-exported from chrome.py** — `from maccat.collectors.chromium import COMPONENT_DENYLIST` in chrome.py; `__all__` includes it.

## Metadata

**Analog search scope:** `src/maccat/collectors/`, `tests/collectors/`
**Files read:** chrome.py, firefox.py, cursor.py, base.py, __init__.py, test_chrome.py, test_cursor.py, test_zed.py, test_section_titles.py
**Pattern extraction date:** 2026-06-17
