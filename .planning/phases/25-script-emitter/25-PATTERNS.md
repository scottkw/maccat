# Phase 25: Script Emitter - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 2 (emitter.py + test_emitter.py)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/maccat/reinstall/emitter.py` | transform/utility | transform (parse-tree → text) | `src/maccat/reinstall/parser.py` | role-match (sibling transform module: same module conventions, same dataclass consumption) |
| `tests/reinstall/test_emitter.py` | test | request-response | `tests/reinstall/test_parser_contract.py` | exact (same test directory, same module under test, same fixture style) + `tests/test_pyz.py` (subprocess call pattern for `bash -n`) |

---

## Pattern Assignments

### `src/maccat/reinstall/emitter.py` (transform, parse-tree → text)

**Analog:** `src/maccat/reinstall/parser.py` (lines 1–235)

**Imports pattern** (parser.py lines 31–36):
```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
```

Copy this shape verbatim, replacing the imports with what the emitter needs:
```python
from __future__ import annotations

import shlex
from functools import partial
from typing import Callable

from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection
```

Key conventions to match:
- `from __future__ import annotations` is ALWAYS line 1
- stdlib imports before project imports, blank line between them
- No third-party imports (stdlib-only rule)

**Module-level ALL_CAPS constants pattern** (parser.py lines 41–52):
```python
SEPARATOR = "-" * 36  # 36 ASCII dashes — matches CatalogWriter.write_section()
NONE_FOUND_SENTINEL = "  (none found)"  # exactly two leading spaces (format.py:56)

DEGRADATION_LINES: frozenset[str] = frozenset(
    {
        "Homebrew is not installed.",
        ...
    }
)
```

The emitter's `SECTION_SOURCE_MAP` follows the same pattern — module-level, ALL_CAPS, typed:
```python
SECTION_SOURCE_MAP: dict[str, Callable[[ParsedSection], str]] = {
    "Homebrew Packages": _brew_block,
    "App Store Applications": _mas_block,
    "VS Code Extensions": partial(_editor_ext_block, editor="code"),
    "Cursor Extensions": partial(_editor_ext_block, editor="cursor"),
}
```

Note: `SECTION_SOURCE_MAP` must be defined AFTER all `_*_block` functions it references (Python module execution order). Place it immediately before `emit_reinstall_script`.

**Section separator comment pattern** (parser.py lines 37–39, 53–55, 75–77):
```python
# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
```

Use the same `# ---...--- / # Section Name / # ---...---` triple for each logical group: injection-safety helpers, section renderers, routing map, public API.

**Dataclass consumption pattern** (parser.py lines 112–126):
```python
def _parse_item_line(raw_line: str) -> ParsedItem:
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

The emitter follows the same pattern: functions take `ParsedSection` or `ParsedItem` dataclasses, access fields by attribute name, return `str` (or `str | None` for per-item helpers). Never access `.raw_line` from the emitter — use `.name`, `.version`, `.id`.

**Docstring style** (parser.py lines 1–30 module docstring, lines 113–117 function docstring):
```python
def _parse_item_line(raw_line: str) -> ParsedItem:
    """Apply ITEM_RE to a single catalog item line. Falls back to name-only on no-match.

    Never raises. Unparseable lines are returned as name-only ParsedItems with
    raw_line preserved.
    """
```

One-line summary, blank line, then expanded explanation. Private helpers get brief docstrings; public API (`emit_reinstall_script`) gets a full Args/Returns docstring.

**`str | None` return type annotation** (parser.py line 86):
```python
id: str | None  # noqa: A003 (shadows builtin; acceptable for domain clarity)
```

The emitter's per-item helpers (`_mas_line`, `_ext_line`) that return `None` for id-less items use the same `str | None` annotation — the pipe union syntax (not `Optional[str]`).

---

### `tests/reinstall/test_emitter.py` (test, request-response)

**Primary analog:** `tests/reinstall/test_parser_contract.py` (lines 1–345)
**Secondary analog:** `tests/test_pyz.py` (lines 1–152) — subprocess call pattern for the `bash -n` test

**Module header pattern** (test_parser_contract.py lines 1–16):
```python
"""Tests for maccat.reinstall.parser — round-trip contract: parse(emit(x)) == x.

Locks the parser <-> catalog/format.py coupling so the two cannot silently drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.catalog.format import emit_item
from maccat.reinstall.parser import (
    _parse_item_line,
    parse_catalog,
)
```

Apply same shape: one-sentence module docstring stating what is locked, `from __future__ import annotations`, stdlib imports, then project imports.

**Test data table pattern** (test_parser_contract.py lines 22–63):
```python
# Six shapes that emit_item() can produce.
# (name, version, id_, exp_name, exp_ver, exp_id)
ROUND_TRIP_CASES = [
    ("Final Cut Pro", "10.7.1", "424389933", "Final Cut Pro", "10.7.1", "424389933"),
    ("Safari", "15.0", "", "Safari", "15.0", None),
    ...
]
```

The emitter test uses the same module-level tuple-list tables, one per concern:
- `BREW_CASES` — items with/without version, expected guard line output
- `MAS_CASES` — items with id, items without id (checklist routing)
- `EXT_CASES` — extension items: mixed-case id, lowercasing, version present/absent
- `ADVERSARIAL_CASES` — shell metacharacters in name/version

**Parametrized test class pattern** (test_parser_contract.py lines 71–136):
```python
class TestItemLineParser:
    """Unit tests for _parse_item_line — pure regex tests, no emit_item."""

    @pytest.mark.parametrize(
        "raw_line,exp_name,exp_ver,exp_id",
        [
            ("Final Cut Pro (10.7.1) [424389933]", "Final Cut Pro", "10.7.1", "424389933"),
            ...
        ],
    )
    def test_parses_all_four_shapes(
        self, raw_line: str, exp_name: str, exp_ver: str | None, exp_id: str | None
    ) -> None:
        """All four canonical emit_item shapes parse to correct name/version/id."""
        item = _parse_item_line(raw_line)
        assert item.name == exp_name
```

Use `class Test<Feature>:` grouping (no `unittest.TestCase`). Parametrize at the method level. All test methods return `-> None`. Assert messages use f-strings: `f"name: {item.name!r} != {exp_name!r}"`.

**`tmp_path` fixture pattern** (test_parser_contract.py lines 252–345):
```python
class TestParseCatalog:
    """Integration tests: parse_catalog() on catalog fragments written to tmp_path."""

    def test_two_section_catalog_returns_both_sections(self, tmp_path: Path) -> None:
        """Two-section catalog yields ParsedCatalog with 2 ParsedSections with correct titles."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_TWO_SECTIONS, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 2
```

For emitter integration tests, construct a `ParsedCatalog` in-memory (no file needed — emitter takes a `ParsedCatalog` object, not a path). Build catalog fixtures as helper functions or module-level factories using the `ParsedCatalog`/`ParsedSection`/`ParsedItem` constructors directly.

**Catalog fragment constants pattern** (test_parser_contract.py lines 206–249):
```python
_CATALOG_TWO_SECTIONS = (
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "git (2.44.0)\n"
    ...
)
```

The emitter test uses `ParsedCatalog` objects instead of text fragments. Follow the same `_SNAKE_CASE_ALL_CAPS` naming for module-level constants that are not test data tables (use plain lowercase `_name` prefix for helper constants, ALL_CAPS only for true constants as in parser).

**`subprocess.run` pattern for the `bash -n` test** (test_pyz.py lines 39–49):
```python
result = subprocess.run(
    [sys.executable, str(PYZ), "--version"],
    cwd=str(tmp_path),
    capture_output=True,
    text=True,
)
assert result.returncode == 0, (
    f"--version failed from {tmp_path!r}:\n"
    f"stdout: {result.stdout!r}\n"
    f"stderr: {result.stderr!r}"
)
```

For the `bash -n` test helper, apply the same `capture_output=True, text=True` options. Add a `pytest.skip()` guard (pattern from test_pyz.py `_require_pyz()` function, lines 27–30):
```python
def _require_pyz() -> None:
    """Skip the calling test if dist/maccat.pyz has not been built."""
    if not PYZ.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")
```

The `bash -n` equivalent:
```python
import shutil
import subprocess
import tempfile
import os

def assert_bash_n_clean(script: str) -> None:
    """Assert the script string passes bash -n syntax check. Skip if bash absent."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(["bash", "-n", tmp], capture_output=True, text=True)
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"
    finally:
        os.unlink(tmp)
```

**`shutil.which` guard pattern** (tests/collectors/test_homebrew.py lines 28–35):
```python
with (
    patch("shutil.which", return_value="/usr/local/bin/brew"),
    patch("subprocess.run", side_effect=[mock_formula, mock_cask]),
):
    result = HomebrewCollector().collect()
```

The emitter test does NOT patch `shutil.which` or `subprocess.run` in emitter tests — the emitter makes no subprocess calls. This pattern appears only in the `assert_bash_n_clean` helper which is a test utility, not the emitter itself.

---

## Shared Patterns

### `from __future__ import annotations` — line 1 in every file
**Source:** `src/maccat/reinstall/parser.py` line 31; `tests/reinstall/test_parser_contract.py` line 6
**Apply to:** Both new files — `emitter.py` and `test_emitter.py`
```python
from __future__ import annotations
```
This is non-negotiable per project conventions. It is ALWAYS the first substantive line (after the module docstring if present, before any imports).

### `str | None` union type syntax (not `Optional`)
**Source:** `src/maccat/reinstall/parser.py` lines 84–86
```python
version: str | None
id: str | None  # noqa: A003
```
**Apply to:** All type annotations in emitter.py and test_emitter.py that express optional strings. Never use `Optional[str]` — the project uses the pipe union form throughout.

### Section separator comment blocks
**Source:** `src/maccat/reinstall/parser.py` lines 37–39
```python
# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
```
**Apply to:** `emitter.py` — use one block per logical grouping: injection helpers, section renderers, routing map, public API.

### `-> None` return type on all test methods
**Source:** `tests/reinstall/test_parser_contract.py` lines 83–86, 104–107
```python
def test_parses_all_four_shapes(
    self, raw_line: str, exp_name: str, exp_ver: str | None, exp_id: str | None
) -> None:
```
**Apply to:** All test methods in `test_emitter.py`. mypy --strict requires explicit `-> None` on all functions including test methods.

### `local` variable names, `snake_case`
**Source:** `src/maccat/reinstall/parser.py` lines 112, 134 — `current_title`, `current_items`, `current_degraded`
**Apply to:** `emitter.py` — all local variables in helper functions use `snake_case`, no single-letter names except loop indices.

### Module docstring before imports
**Source:** `src/maccat/reinstall/parser.py` lines 1–30
```python
"""Catalog parser — inverts emit_item() line shapes into typed dataclasses.

parse_catalog(path) -> ParsedCatalog is the public API consumed by the
Phase 25 reinstall emitter. ...
"""
from __future__ import annotations
```
**Apply to:** Both new files. Module docstring goes before `from __future__ import annotations`. For emitter.py, document: what the module does, its zero-subprocess constraint, and the injection-safety design (two-function gate: `quote_for_script` for command position, `safe_comment_value` for comment context).

---

## No Analog Found

No files in this phase lack a codebase analog. Both files have strong matches.

| File | Role | Data Flow | Notes |
|---|---|---|---|
| (none) | — | — | All files have analogs |

The `bash -n` subprocess test pattern is covered by `tests/test_pyz.py` as a secondary analog. The `functools.partial` + mypy --strict open question (RESEARCH.md Assumption A1) has no existing codebase example — if mypy --strict rejects `partial(...)` for `Callable[[ParsedSection], str]`, fall back to `lambda section: _editor_ext_block(section, editor="code")` (mypy-friendly, same behavior; no existing analog needed).

---

## Metadata

**Analog search scope:** `src/maccat/reinstall/`, `src/maccat/catalog/`, `tests/reinstall/`, `tests/`, `tests/collectors/`
**Files scanned:** 6 (parser.py, format.py, test_parser_contract.py, conftest.py, test_pyz.py, test_homebrew.py)
**Pattern extraction date:** 2026-06-16
