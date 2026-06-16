# Phase 24: Catalog Format Fix + Parser Foundation - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 6 (2 modified, 4 created)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/maccat/collectors/mas.py` | collector | transform | `src/maccat/collectors/homebrew.py` | exact |
| `tests/collectors/test_homebrew.py` | test | — | `tests/collectors/test_homebrew.py` (self) | self-update |
| `src/maccat/reinstall/__init__.py` | subpackage init | — | `src/maccat/helpers/__init__.py` | exact |
| `src/maccat/reinstall/parser.py` | utility / transform | file-I/O + transform | `src/maccat/catalog/format.py` | role-match |
| `tests/reinstall/__init__.py` | test init | — | `tests/collectors/__init__.py` | exact |
| `tests/reinstall/test_parser_contract.py` | test | — | `tests/test_format.py` | exact |

---

## Pattern Assignments

### `src/maccat/collectors/mas.py` (collector, transform)

**Analog:** `src/maccat/collectors/mas.py` (self) — rewrite of `_parse_mas_output` only; all other structure unchanged.

**Imports pattern** (lines 1–8) — copy verbatim, add `emit_item` import inside the method per anti-pattern note in RESEARCH.md:
```python
"""MasCollector — raw-write byte-parity with update-list.sh:2249."""
from __future__ import annotations

import shutil
import subprocess
import sys

from maccat.collectors.base import Collector, CollectorResult, Section
```

**Core pattern — new `_parse_mas_output`** (replaces lines 27–45):
```python
def _parse_mas_output(self, stdout: str) -> list[str]:
    """Extract id, multi-word name, and version from mas list output.

    Real mas list format: '<id>  <MultiWordName> (<version>)'
    Column 1: numeric App Store ID
    Columns 2..N-1: multi-word app name (joined with spaces)
    Column N: version wrapped in parens — strip before passing to emit_item.

    Routes through emit_item(name, version, id_) for FMT-01 compliance.
    """
    from maccat.catalog.format import emit_item

    lines: list[str] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        id_ = parts[0]
        last = parts[-1]
        if len(parts) >= 3 and last.startswith("(") and last.endswith(")"):
            version = last[1:-1]          # strip single parens; avoids ((version))
            name = " ".join(parts[1:-1])  # middle fields: multi-word app name
        else:
            version = ""                  # no version; degrade gracefully
            name = " ".join(parts[1:])
        item = emit_item(name, version, id_)
        if item is not None:
            lines.append(item)
    return lines
```

**Structure preserved from existing file** (lines 47–79) — `collect()` body is unchanged. The fallback `Section` returns (not-installed, non-zero exit) stay identical. Only `_parse_mas_output` is replaced.

**Key rule from analog:** The deferred `from maccat.catalog.format import emit_item` inside the method body is the established pattern for avoiding circular imports in collectors (see `collectors/__init__.py` lines 42–53 where all collector imports are deferred inside `get_registry()`).

---

### `tests/collectors/test_homebrew.py` (test, self-update)

**Analog:** `tests/collectors/test_homebrew.py` (self) — update three assertions in `TestMasCollector`.

**Test class structure pattern** (lines 115–188) — copy the class/method structure verbatim, update only the marked assertions:

```python
class TestMasCollector:
    def test_mas_collect_parses_output(self) -> None:
        """mas available — output parsed, id preserved in [id] bracket, raw=True."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "1234567890  Safari (15.0)\n9876543210  Xcode (14.0)"

        with (
            patch("shutil.which", return_value="/usr/local/bin/mas"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = MasCollector().collect()

        section = result.sections[0]
        # OLD: assert section.items == ["Safari (15.0)", "Xcode (14.0)"]
        assert section.items == ["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]
        assert section.raw is True
```

**Test to replace** — `test_mas_two_field_line_emits_trailing_space` (lines 167–180) becomes invalid. Its docstring described awk parity with trailing space; replace with:
```python
def test_mas_two_field_line_degrades_to_name_id(self) -> None:
    """2-field line ('123  OnlyTwo') — no version; emits 'OnlyTwo [123]' via emit_item."""
    mas = MasCollector()
    result = mas._parse_mas_output("123  OnlyTwo\n456  Safari (15.0)")
    assert result == ["OnlyTwo [123]", "Safari (15.0) [456]"]
```

**Test structure conventions** (from `test_homebrew.py` throughout):
- `from __future__ import annotations` at top (line 1)
- `from unittest.mock import MagicMock, patch` (line 7)
- Class-based grouping: `TestMasCollector` stays as-is
- Docstring on every method (imperative sentence — "X condition → Y result")
- `with patch(...):` context manager for subprocess mocking
- `assert section.raw is True` after every collect() assertion

---

### `src/maccat/reinstall/__init__.py` (subpackage init)

**Analog:** `src/maccat/helpers/__init__.py` (line 1) and `src/maccat/catalog/__init__.py` (line 1)

**Pattern** — one-line docstring, no imports:
```python
"""Reinstall script generation — catalog parser and emitter."""
```

`helpers/__init__.py` is exactly `"""Shared helper utilities."""` (one line). `catalog/__init__.py` is `"""Catalog output format layer."""`. Match that minimal pattern: one descriptive module docstring, nothing else. Do NOT re-export symbols here — the `__init__.py` for `collectors/` shows that re-exports belong only when an explicit `__all__` list is justified; for a two-file subpackage the parser's public API is imported directly by callers.

---

### `src/maccat/reinstall/parser.py` (utility, file-I/O + transform)

**Primary analog:** `src/maccat/catalog/format.py` — same module role (pure transform functions + module-level constants, no class, stdlib only).

**Secondary analog:** `src/maccat/collectors/base.py` — dataclass pattern with `field(default_factory=list)`.

**Imports pattern** — combine both analogs:
```python
"""Catalog parser — inverts emit_item() line shapes into typed dataclasses.

parse_catalog(path) -> ParsedCatalog is the public API consumed by the
Phase 25 reinstall emitter.  The parser is the logical inverse of
catalog/format.py::emit_item(); do NOT import emit_item here to avoid
coupling (the regex is the sole contract between the two modules).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
```

`from __future__ import annotations` is line 1 in every module in this codebase (verified: `format.py` line 1, `base.py` line 1, `json_io.py` line 1, `writer.py` line 1).

**Dataclass pattern** — from `src/maccat/collectors/base.py` lines 9–19:
```python
@dataclass
class Section:
    title: str
    items: list[str]
    raw: bool = False
```
Copy that `@dataclass` + field-per-line style. The new dataclasses follow the same pattern:
```python
@dataclass
class ParsedItem:
    name: str
    version: str | None
    id: str | None       # noqa: A003 (shadows builtin; acceptable for domain clarity)
    raw_line: str

@dataclass
class ParsedSection:
    title: str
    items: list[ParsedItem] = field(default_factory=list)
    degraded: bool = False

@dataclass
class ParsedCatalog:
    sections: list[ParsedSection] = field(default_factory=list)
    path: str = ""       # str not Path — serialization-friendly
```

**Module-level constant pattern** — from `src/maccat/catalog/format.py` (no named constants, logic in functions) and `src/maccat/collectors/mas.py` line 10 (`TITLE = "App Store Applications"`). Define sentinel and degradation strings as module-level constants:
```python
SEPARATOR = "-" * 36          # 36 ASCII dashes — matches CatalogWriter.write_section()
NONE_FOUND_SENTINEL = "  (none found)"   # exactly two leading spaces (format.py:56)

DEGRADATION_LINES: frozenset[str] = frozenset({
    "Homebrew is not installed.",
    "mas (Mac App Store CLI) is not installed.",
    "Install it with Homebrew: brew install mas",
    "Could not retrieve App Store list.",
    "Setapp is not installed or detected.",
})
```

**Regex constant pattern** — module-level `re.compile` (mirrors `format.py` approach of module-level pure logic, no class):
```python
ITEM_RE = re.compile(
    r"^"
    r"(?P<name>.+?)"
    r"(?:"
        r"\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"   # branch 1: version + id
    r"|"
        r"\s+\((?P<version2>[^)]+)\)"                         # branch 2: version only
    r"|"
        r"\s+\[(?P<id2>[^\]]+)\]"                             # branch 3: id only
    r")?"
    r"$"
)
```
Note: named groups must use distinct names across alternation branches (`version`/`version2`, `id`/`id2`) to avoid Python `re` redefinition error (see RESEARCH.md Pitfall 6).

**Core function pattern** — `parse_catalog` follows the same function signature style as `flush_section` in `format.py` (type-annotated, docstring, pure function):
```python
def parse_catalog(path: Path) -> ParsedCatalog:
    """Read a catalog file and return typed structured items.

    Inverts all four emit_item() line shapes and their degradations.
    Encoding: UTF-8 (matches CatalogWriter which writes with encoding='utf-8').
    """
    ...
```

**Internal helper pattern** — prefix private helpers with `_` (matches `_parse_mas_output`, `_parse_brew_versions_line` naming in collectors):
```python
def _parse_item_line(raw_line: str) -> ParsedItem:
    """Apply ITEM_RE to a single catalog item line. Falls back to name-only on no-match."""
    m = ITEM_RE.match(raw_line)
    if not m:
        return ParsedItem(name=raw_line, version=None, id=None, raw_line=raw_line)
    return ParsedItem(
        name=m.group("name"),
        version=m.group("version") or m.group("version2"),
        id=m.group("id") or m.group("id2"),
        raw_line=raw_line,
    )
```

**Error handling pattern** — from `json_io.py` lines 26–41 (graceful degradation, never raises). The parser must never crash; fallback to name-only `ParsedItem` on unparseable lines, identical pattern:
```python
# json_io.py reference: every error path returns default, never raises
except (json.JSONDecodeError, OSError, UnicodeDecodeError):
    return default
```
Parser equivalent: `ITEM_RE.match()` always returns a match object or None; the `if not m:` branch is the only error path, and it returns a valid (degraded) `ParsedItem`.

**File I/O pattern** — from `catalog/writer.py` line 43 (`encoding="utf-8"`) and `json_io.py` line 30 (`file.read_text(encoding="utf-8")`). Always explicit UTF-8:
```python
text = path.read_text(encoding="utf-8")
```

---

### `tests/reinstall/__init__.py` (test init)

**Analog:** `tests/collectors/__init__.py` and `tests/helpers/__init__.py` — both are empty files (0 bytes).

**Pattern:** Empty file. No docstring, no content. This is consistent across all `tests/` subdirectory `__init__.py` files in this project.

---

### `tests/reinstall/test_parser_contract.py` (test, round-trip contract)

**Primary analog:** `tests/test_format.py` — same structure: parametrized test classes, `from __future__ import annotations`, imports from the module under test, class-per-behavior grouping.

**Secondary analog:** `tests/helpers/test_plist_version.py` — shows tmp_path fixture usage and edge-case docstring style.

**Imports pattern** — from `tests/test_format.py` lines 1–12:
```python
"""Tests for maccat.reinstall.parser — round-trip contract: parse(emit(x)) == x.

Locks the parser <-> catalog/format.py coupling so the two cannot silently drift.
"""
from __future__ import annotations

import pytest
from maccat.catalog.format import emit_item
from maccat.reinstall.parser import (
    ParsedCatalog,
    ParsedItem,
    ParsedSection,
    _parse_item_line,
    parse_catalog,
)
```

**Parametrized test pattern** — from `tests/test_format.py` lines 80–125. The project uses `@pytest.mark.parametrize` for table-driven tests:
```python
ROUND_TRIP_CASES = [
    # (name, version, id_, exp_name, exp_ver, exp_id)
    ("Final Cut Pro", "10.7.1", "424389933", "Final Cut Pro", "10.7.1", "424389933"),
    ...
]

@pytest.mark.parametrize("name,version,id_,exp_name,exp_ver,exp_id", ROUND_TRIP_CASES)
def test_round_trip(name: str, ...) -> None:
    ...
```

**Class-per-behavior grouping pattern** — from `tests/test_format.py` lines 19, 67, 132 (three classes: `TestEmitItem`, `TestFlushSection`, `TestVersionSortTail`). Use the same pattern:
```python
class TestItemLineParser:        # unit tests for _parse_item_line
class TestRoundTrip:             # parametrized round-trip: emit -> parse -> re-emit
class TestAdversarialFixtures:   # embedded parens/brackets in names
class TestParseCatalog:          # integration: parse_catalog() with tmp_path fixture
```

**`tmp_path` fixture pattern** — from `tests/helpers/test_plist_version.py` lines 15–23:
```python
def test_returns_bundle_short_version(self, tmp_path: Path) -> None:
    plist_file = tmp_path / "Info.plist"
    plist_file.write_bytes(...)
    assert get_plist_version(plist_file) == "3.8.4"
```
Use `tmp_path` for `parse_catalog()` integration tests — write a catalog fragment via `Path.write_text(encoding="utf-8")`, then call `parse_catalog(tmp_path / "catalog.txt")` and assert on the returned `ParsedCatalog`.

**Docstring style** — every test method has a one-line docstring in imperative sentence form describing "condition → result" (from `test_homebrew.py` throughout, e.g. line 19: `"""brew available — formulae+cask lines emitted as 'name (version)', raw=True."""`).

**Adversarial fixture documentation pattern** — the lossy round-trip cases must be explicitly documented per RESEARCH.md. Use a `round_trip_ok: bool` parameter and a comment:
```python
# KNOWN LOSSY: embedded paren in name without a version field is ambiguous
("App (Beta) [999]", "App", "Beta", "999", False),
```

---

## Shared Patterns

### `from __future__ import annotations` — line 1 in every module
**Source:** `src/maccat/catalog/format.py` line 1, `src/maccat/collectors/base.py` line 1, `src/maccat/helpers/json_io.py` line 1, `src/maccat/catalog/writer.py` line 1
**Apply to:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
```python
from __future__ import annotations
```

### Graceful degradation — never crash, return sentinel
**Source:** `src/maccat/collectors/mas.py` lines 48–77 (fallback Section on missing tool or non-zero exit); `src/maccat/helpers/json_io.py` lines 26–41 (try/except returns default)
**Apply to:** `src/maccat/reinstall/parser.py` (`_parse_item_line` fallback, sentinel/degradation detection)

The pattern: check the error condition first, return a valid (empty/degraded) result — never raise from a data-parsing function.

### Deferred internal imports to avoid circular coupling
**Source:** `src/maccat/collectors/__init__.py` lines 42–53 (all collector imports inside `get_registry()`); `src/maccat/reinstall/parser.py` should NOT import `emit_item` (circular coupling risk)
**Apply to:** `src/maccat/collectors/mas.py` `_parse_mas_output` — import `emit_item` at the top of the method body (`from maccat.catalog.format import emit_item`) to keep the import localized and the test mock surface small.

### Module-level constants in ALL_CAPS
**Source:** `src/maccat/collectors/mas.py` line 10 (`TITLE = "App Store Applications"`); `src/maccat/catalog/format.py` (no constants, but `flush_section` uses `["  (none found)"]` inline — the parser should name this)
**Apply to:** `src/maccat/reinstall/parser.py` — `SEPARATOR`, `NONE_FOUND_SENTINEL`, `DEGRADATION_LINES`, `ITEM_RE`

### Test file header docstring
**Source:** `tests/test_format.py` lines 1–6; `tests/collectors/test_homebrew.py` lines 1–4; `tests/helpers/test_plist_version.py` lines 1–5
**Apply to:** `tests/reinstall/test_parser_contract.py`
```python
"""Tests for maccat.reinstall.parser — [brief behavioral spec reference]."""
from __future__ import annotations
```

---

## No Analog Found

All files in this phase have close analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `src/maccat/`, `tests/`
**Files read:** 13 source + test files
**Pattern extraction date:** 2026-06-16
