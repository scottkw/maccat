# Phase 30: Markdown Emitter & `.md` Plumbing - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 13 (7 source + 6 test)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/maccat/catalog/markdown.py` | formatter / renderer | transform | `src/maccat/reinstall/emitter.py` | role-match (pure renderer, no I/O) |
| `src/maccat/catalog/writer.py` | utility / writer | file-I/O | self (minor addition) | exact |
| `src/maccat/naming.py` | utility / naming | transform | self (regex + format string swap) | exact |
| `src/maccat/retention.py` | utility / retention | file-I/O | self (glob string swap) | exact |
| `src/maccat/identity.py` | utility / identity | file-I/O | self (glob string swap, 2 sites) | exact |
| `src/maccat/cli.py` | orchestrator | request-response | self (generate loop replacement) | exact |
| `tests/test_markdown_emitter.py` | test | transform | `tests/reinstall/test_emitter.py` | role-match |
| `tests/test_naming.py` | test | transform | self (assertion string updates) | exact |
| `tests/test_retention.py` | test | file-I/O | self (assertion string updates) | exact |
| `tests/test_safety_invariants.py` | test | file-I/O | self (one literal filename update) | exact |
| `tests/test_cli.py` | test | request-response | self (5 glob assertion updates) | exact |
| `tests/conftest.py` | test fixture | — | self (auto-inherits via naming.py) | exact |

---

## Pattern Assignments

### `src/maccat/catalog/markdown.py` (new file — formatter, transform)

**Analog:** `src/maccat/reinstall/emitter.py`

The reinstall emitter is the closest structural analog: a pure Python module with no subprocess calls, no side effects, that takes parsed catalog data and returns a `str`. The markdown emitter follows the same shape.

**Module header pattern** (`src/maccat/reinstall/emitter.py` lines 1–14):
```python
"""Reinstall script emitter — renders a ParsedCatalog into a complete reinstall.sh string.

This module makes no process calls: it builds the script text entirely in Python and
returns a str. The caller (Phase 26) writes the string to disk ...
"""
from __future__ import annotations

import shlex
from collections.abc import Callable

from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection
```

For `markdown.py`, the analogous imports are:
```python
from __future__ import annotations

import re
from maccat.collectors.base import Section
from maccat.catalog.format import flush_section
```

**`ITEM_RE` regex to copy from** (`src/maccat/reinstall/parser.py` lines 61–73 — duplicate, do not import):
```python
ITEM_RE = re.compile(
    r"^"
    r"(?P<name>.+?)"                                             # non-greedy name
    r"(?:"
    r"\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"          # branch 1: version + id
    r"|"
    r"\s+\((?P<version2>[^)]+)\)"                               # branch 2: version only
    r"|"
    r"\s+\[(?P<id2>[^\]]+)\]"                                   # branch 3: id only
    r")?"
    r"\s*"                                                       # WR-04: trailing whitespace
    r"$"
)
```

**`DEGRADATION_LINES` frozenset to copy from** (`src/maccat/reinstall/parser.py` lines 44–52):
```python
DEGRADATION_LINES: frozenset[str] = frozenset(
    {
        "Homebrew is not installed.",
        "mas (Mac App Store CLI) is not installed.",
        "Install it with Homebrew: brew install mas",
        "Could not retrieve App Store list.",
        "Setapp is not installed or detected.",
    }
)
```
Duplicate this constant into `markdown.py` verbatim — do not import from `reinstall/parser.py` (avoids coupling to the reinstall module).

**`NONE_FOUND_SENTINEL` to check against** (`src/maccat/reinstall/parser.py` line 41):
```python
NONE_FOUND_SENTINEL = "  (none found)"  # exactly two leading spaces (format.py:56)
```
In the markdown emitter, check for `flush_section([])`'s return value `["  (none found)"]` before rendering a table. An empty-items section after flush yields this sentinel; a degradation-line section has items all in `DEGRADATION_LINES`.

**Section-skip logic pattern** (`src/maccat/reinstall/emitter.py` lines 55–62):
```python
def _should_skip(section: ParsedSection) -> bool:
    """Return True for degraded sections and legitimately empty sections."""
```
Analogous in `markdown.py`: detect degraded/empty before calling `_render_table`.

**Pure-function public API pattern** (`src/maccat/reinstall/emitter.py`):
```python
def emit_reinstall_script(catalog: ParsedCatalog) -> str:
    """Return the complete reinstall.sh content as a single string."""
```
The markdown analog:
```python
def render_markdown_catalog(
    sections: list[Section],
    *,
    computer: str,
    hostname: str,
    generated: str,           # ISO-8601 local: "2026-06-18T12:34:56"
    maccat_version: str,
) -> str:
    """Return the complete .md catalog content as a single string."""
```

**`flush_section` call pattern for non-raw sections** (`src/maccat/cli.py` lines 325–327):
```python
if section.raw:
    w.write_lines(section.items)
else:
    w.write_lines(flush_section(section.items))
```
In `render_markdown_catalog`, apply `flush_section()` only when `not section.raw`. Raw sections (Homebrew, mas) pass items to `_render_table` as-is.

---

### `src/maccat/catalog/writer.py` (minor addition — utility, file-I/O)

**Analog:** self

**Existing `write_lines` method to follow as a style pattern** (lines 70–78):
```python
def write_lines(self, lines: list[str]) -> None:
    """Append sorted lines (from flush_section) — each line gets exactly one trailing \\n."""
    assert self._fh is not None, "write_lines called outside context manager"
    for line in lines:
        self._fh.write(line + "\n")
```

**New `write_raw` method to add** — follows the same assert-then-write pattern:
```python
def write_raw(self, content: str) -> None:
    """Write pre-rendered content (e.g. full markdown string) to the catalog file.

    The caller is responsible for encoding correctness and trailing newline.
    Content is written in a single call; partial writes cannot occur.
    """
    assert self._fh is not None, "write_raw called outside context manager"
    self._fh.write(content)
```
The file handle is opened as `encoding="utf-8", newline="\n"` (line 43) — no encoding parameter needed in `write_raw`.

---

### `src/maccat/naming.py` (regex + format string swap — utility, transform)

**Analog:** self

**Current `_FILENAME_RE`** (line 18–20):
```python
_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)
```
Change `\.txt$` to `\.md$`.

**Current `make_catalog_filename`** (line 71):
```python
return f"mac-software-list-[{machine}]-{timestamp}.txt"
```
Change `.txt` to `.md`.

**Docstring convention to update** (line 8 and line 69): update the literal `.txt` references in the module-level docstring and `make_catalog_filename` docstring to `.md`.

---

### `src/maccat/retention.py` (three glob strings — utility, file-I/O)

**Analog:** self

**Three glob sites to change** (`retention.py`):

Line 64 (pass 1 of `retain_newest_per_host`):
```python
for f in target_dir.glob("mac-software-list-*.txt"):
# → change to:
for f in target_dir.glob("mac-software-list-*.md"):
```

Line 75 (pass 2 of `retain_newest_per_host`):
```python
for f in target_dir.glob("mac-software-list-*.txt"):
# → change to:
for f in target_dir.glob("mac-software-list-*.md"):
```

Line 118 (`prune_old_archives`):
```python
for f in archive_dir.glob("mac-software-list-*.txt"):
# → change to:
for f in archive_dir.glob("mac-software-list-*.md"):
```

**Docstrings** (lines 41–42 and 96–97) reference `mac-software-list-*.txt` — update to `.md`. The function logic (parse, compare timestamps, warn-and-continue) is entirely unchanged.

---

### `src/maccat/identity.py` (two glob strings — utility, file-I/O)

**Analog:** self

**Site 1** — `discover_computer_folders()` (line 158):
```python
if any(d.glob("mac-software-list-*.txt")):
# → change to:
if any(d.glob("mac-software-list-*.md")):
```

**Site 2** — `rename_machine()` rewrite loop (line 549):
```python
for file_path in rewrite_dir.glob("mac-software-list-*.txt"):
# → change to:
for file_path in rewrite_dir.glob("mac-software-list-*.md"):
```

No other logic changes in `identity.py`.

---

### `src/maccat/cli.py` (generate loop replacement — orchestrator, request-response)

**Analog:** self

**Existing generate loop** (lines 306–327) to replace:
```python
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

filename = make_catalog_filename(computer, timestamp)
output_file = catalog_repo / computer / filename
(catalog_repo / computer).mkdir(parents=True, exist_ok=True)

with CatalogWriter(output_file) as w:
    w.write_section("Installed Mac Software List")
    for collector in get_registry():
        result = collector.collect()
        for section in result.sections:
            w.write_section(section.title)
            if section.raw:
                w.write_lines(section.items)
            else:
                w.write_lines(flush_section(section.items))
```

**Replacement pattern** (following the same outer structure):
```python
import socket   # add to top-level imports (stdlib, already used in identity.py)

now = datetime.now()
timestamp = now.strftime("%Y%m%d%H%M%S")
generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")

all_sections: list[Section] = []
for collector in get_registry():
    result = collector.collect()
    all_sections.extend(result.sections)

from maccat.catalog.markdown import render_markdown_catalog
content = render_markdown_catalog(
    all_sections,
    computer=computer,
    hostname=socket.gethostname(),
    generated=generated_iso,
    maccat_version=__version__,
)

filename = make_catalog_filename(computer, timestamp)
output_file = catalog_repo / computer / filename
(catalog_repo / computer).mkdir(parents=True, exist_ok=True)

with CatalogWriter(output_file) as w:
    w.write_raw(content)
```

**`from maccat import __version__`** — already present in `_build_parser()` (line 41) via a deferred import. In `run()` it must be imported before the `render_markdown_catalog` call; follow the same deferred import pattern used in the rest of `cli.py`:
```python
from maccat import __version__
```

**`Section` type import** — add to `run()` body's deferred imports alongside `CatalogWriter`:
```python
from maccat.collectors.base import Section
```

---

### `tests/test_markdown_emitter.py` (new test file — test, transform)

**Analog:** `tests/reinstall/test_emitter.py`

**Module header and import pattern** (`tests/reinstall/test_emitter.py` lines 1–21):
```python
"""Tests for maccat.reinstall.emitter — locks emitter rendering correctness ..."""
from __future__ import annotations

import pytest

from maccat.reinstall.emitter import (
    emit_reinstall_script,
    ...
)
from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection
```

Analogous for `test_markdown_emitter.py`:
```python
"""Tests for maccat.catalog.markdown — locks render_markdown_catalog correctness."""
from __future__ import annotations

import pytest

from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section
```

**Test class structure pattern** — follow the class-per-concern grouping used in `test_format.py` (e.g. `TestEmitItem`, `TestFlushSection`) and `test_emitter.py`:
```python
class TestFrontmatter: ...        # frontmatter key order, YAML quoting of generated
class TestTableRendering: ...     # 3-column header, cell values, empty cells as " "
class TestPipeEscaping: ...       # | in cell value -> \|
class TestEmptySections: ...      # (none found) plain text, no empty table
class TestDegradedSections: ...   # degradation lines -> (none found)
class TestRawVsNonRaw: ...        # raw=True skips flush_section, raw=False applies it
class TestDeterminism: ...        # byte-identical output with fixed timestamp
```

**Determinism test pattern** (`tests/test_format.py` lines 85–99 and `tests/reinstall/test_parser_contract.py` structure):
```python
def test_render_deterministic(self) -> None:
    FIXED_TS = "2026-06-18T12:34:56"
    sections = [Section(title="Homebrew Packages", items=["git (2.44.0)", "zsh (5.9)"], raw=True)]
    result1 = render_markdown_catalog(
        sections, computer="MyMac", hostname="my-mac.local",
        generated=FIXED_TS, maccat_version="2.1.0"
    )
    result2 = render_markdown_catalog(
        sections, computer="MyMac", hostname="my-mac.local",
        generated=FIXED_TS, maccat_version="2.1.0"
    )
    assert result1 == result2
```

**Parametrized test pattern** (from `tests/reinstall/test_parser_contract.py` lines 74–81):
```python
@pytest.mark.parametrize(
    "raw_line,exp_name,exp_ver,exp_id",
    [
        ("git (2.44.0)", "git", "2.44.0", ""),
        ("Final Cut Pro (10.7.1) [424389933]", "Final Cut Pro", "10.7.1", "424389933"),
        ...
    ]
)
def test_parse_columns(self, raw_line, exp_name, exp_ver, exp_id) -> None: ...
```

---

### `tests/test_naming.py` (assertion string updates — test, transform)

**Analog:** self

Every literal `.txt` string in this file must become `.md`. The five test methods affected:

- `test_valid_filename_returns_dataclass` (line 20): `"mac-software-list-[personal]-20260614120000.txt"` → `.md`
- `test_machine_field_populated_correctly` (line 25): same
- `test_timestamp_field_populated_correctly` (line 30): same
- `test_filename_field_preserved` (line 34–35): same
- `test_spaces_in_machine_name_allowed` (line 40): `"mac-software-list-[My Computer]-20260614120000.txt"` → `.md`
- `test_brackets_in_machine_name_returns_none` (line 59): change to `.md`
- `test_13_digit_timestamp_returns_none` (line 63): change to `.md`
- `test_15_digit_timestamp_returns_none` (line 67): change to `.md`
- `test_missing_txt_extension_returns_none` (line 93): change assert description string; the `test_wrong_extension_returns_none` test (line 92–95) should be updated to try `.txt` (now the wrong extension)
- `test_output_format` (line 108–109): `assert result == "mac-software-list-[personal]-20260614120000.txt"` → `.md`
- `test_brackets_wrap_machine` (line 135–137): content check unchanged; passes automatically

Note: `test_missing_txt_extension_returns_none` (line 92) — after the change, `.txt` is the wrong extension and should return None. This test remains valid but the description should clarify it's testing the `.txt` extension (now wrong). Alternatively, rename to `test_txt_extension_returns_none`.

---

### `tests/test_retention.py` (assertion string updates — test, file-I/O)

**Analog:** self

All `_touch_catalog` helper calls in this file use `make_catalog_filename()` which auto-inherits `.md` once `naming.py` is changed — no manual edits needed for those.

Any hardcoded literal `.txt` filename strings (if present) must be updated to `.md`. The `_touch_catalog` helper (line 24–27) uses `make_catalog_filename` so it auto-updates:
```python
def _touch_catalog(directory: Path, machine: str, timestamp: str) -> Path:
    p = directory / make_catalog_filename(machine, timestamp)
    p.write_text("", encoding="utf-8")
    return p
```
No manual changes needed in `test_retention.py` unless there are inline literal `.txt` strings not going through `make_catalog_filename`.

---

### `tests/test_safety_invariants.py` (one literal filename — test, file-I/O)

**Analog:** self

**One site that requires a manual edit** (line 60):
```python
weird = archive / "mac-software-list-[alpha]-2026.txt"
```
Must become:
```python
weird = archive / "mac-software-list-[alpha]-2026.md"
```
The invariant test requires the file to match the glob (`mac-software-list-*.md` after the change) but fail `parse_catalog_filename` due to a 4-digit timestamp. Keeping `.txt` after the change would make the file invisible to the `.md` glob — the safety-skip branch would never fire and the assertion would pass vacuously (same bug the comment on line 46–51 warns about for the prior fixture).

---

### `tests/test_cli.py` (5 glob assertion updates — test, request-response)

**Analog:** self

Five `glob("mac-software-list-*.txt")` calls to update to `.md`. **These require manual edits** — they are not routed through `make_catalog_filename`.

Line 241:
```python
txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
# → change to:
md_files = list(mymac_dir.glob("mac-software-list-*.md"))
```
Update variable name `txt_files` → `md_files` and the corresponding assert message on line 242–244.

Line 290–291:
```python
txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
assert len(txt_files) >= 1, "Catalog file should have been written"
```

Line 295–298:
```python
archived = list(archive_dir.glob("mac-software-list-*.txt"))
assert len(archived) == 0, ...
```

Line 334–335:
```python
txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
assert len(txt_files) >= 1, "Catalog file should exist after run"
```

Line 469 (search for the fifth site):
```python
# Same pattern — update glob to *.md and variable name to md_files
```

The surrounding monkeypatch and assert logic is unchanged; only the glob extension string and variable name change.

---

### `tests/conftest.py` (automatic via naming.py — test fixture)

**No manual edit required.** The `catalog_repo` fixture (line 53) calls `make_catalog_filename("personal", "20260614120000")` which auto-returns `.md` once `naming.py` is updated:
```python
catalog = computer_dir / make_catalog_filename("personal", "20260614120000")
catalog.write_text("test catalog", encoding="utf-8")
```
The fixture auto-inherits the extension change.

---

## Shared Patterns

### Module-level `from __future__ import annotations`
**Source:** Every file in `src/maccat/`
**Apply to:** `catalog/markdown.py` (new file)
```python
from __future__ import annotations
```
All maccat modules begin with this — include it in the new file.

### Warn-and-continue / never-raise policy
**Source:** `src/maccat/retention.py` (lines 69–70, 84–87) and `src/maccat/reinstall/parser.py` (lines 118–120)
**Apply to:** `catalog/markdown.py` — the `_parse_columns` internal helper
```python
def _parse_columns(line: str) -> tuple[str, str, str]:
    m = _ITEM_RE.match(line)
    if not m:
        return line, "", ""   # never raise — fall back to name-only
    ...
```

### Subprocess sort invariant
**Source:** `src/maccat/catalog/format.py` (lines 46–73), docstring:
```
CRITICAL: Do NOT use Python built-in sort here — it diverges from LC_ALL=C
sort -f for mixed-case and non-ASCII names.
```
**Apply to:** `catalog/markdown.py` — call `flush_section()` from `catalog.format` for non-raw sections. Never use `sorted()`.

### Atomic write via `CatalogWriter`
**Source:** `src/maccat/catalog/writer.py` lines 38–57
**Apply to:** `cli.py` generate loop — keep `CatalogWriter` as the write path; use `write_raw(content)` after `render_markdown_catalog` returns.

### `assert self._fh is not None` guard
**Source:** `src/maccat/catalog/writer.py` lines 65, 74 (both existing methods)
**Apply to:** new `write_raw` method in `writer.py`:
```python
assert self._fh is not None, "write_raw called outside context manager"
```

### Deferred imports in `cli.py`
**Source:** `src/maccat/cli.py` line 14 comment: "All maccat.* imports are DEFERRED inside function bodies"
**Apply to:** `from maccat.catalog.markdown import render_markdown_catalog` — place inside `run()` body with the other deferred imports, not at the top of `cli.py`.

---

## No Analog Found

All files have close analogs. No "no analog" entries.

---

## Metadata

**Analog search scope:** `src/maccat/`, `tests/`
**Files read:** 15 source files + 7 test files
**Pattern extraction date:** 2026-06-18
