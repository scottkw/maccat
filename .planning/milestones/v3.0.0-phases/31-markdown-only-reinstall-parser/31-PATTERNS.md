# Phase 31: Markdown-Only Reinstall Parser - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/maccat/reinstall/parser.py` (addition) | parser / utility | transform (file-I/O → dataclass) | `src/maccat/reinstall/parser.py` itself (existing `parse_catalog`) | exact — same file, co-located additions |
| `src/maccat/reinstall/cli.py` (minor update) | orchestrator / middleware | request-response (args → file write) | `src/maccat/reinstall/cli.py` itself (existing `run_reinstall`) | exact — same file, one-line except expansion |
| `tests/reinstall/test_parser_contract.py` (addition) | test — contract/round-trip | transform | `tests/reinstall/test_parser_contract.py` itself (`TestRoundTrip`, `TestParseCatalog`) | exact — same file, new classes added alongside existing ones |
| `tests/reinstall/test_reinstall_cli.py` (fixture update) | test — integration | request-response | `tests/reinstall/test_reinstall_cli.py` itself | exact — same file, fixture constants updated |
| `tests/reinstall/test_picker_and_reinstall_cli.py` (fixture update) | test — integration | request-response | `tests/reinstall/test_picker_and_reinstall_cli.py` itself | exact — same file, fixture constants updated |

---

## Pattern Assignments

### `src/maccat/reinstall/parser.py` — new functions `_unescape_cell`, `_parse_markdown_row`, `parse_markdown_catalog`

**Analog:** `src/maccat/reinstall/parser.py` — existing `_parse_item_line` and `parse_catalog`

**Imports pattern** (lines 31–35):
```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
```
No new imports needed. `re` is already present but not needed by the markdown parser; `pathlib.Path` and `dataclasses` are already imported.

**Module-level constants pattern** (lines 40–52):
```python
SEPARATOR = "-" * 36
NONE_FOUND_SENTINEL = "  (none found)"

DEGRADATION_LINES: frozenset[str] = frozenset(
    {
        "Homebrew is not installed.",
        ...
    }
)
```
The markdown parser needs its own sentinel string: `"(none found)"` (no leading spaces — the emitter writes it without indentation at `catalog/markdown.py` line 202). Do NOT reuse `NONE_FOUND_SENTINEL` (which has two leading spaces for the legacy format). Define a new module-level constant or inline the literal.

**Internal helper pattern** (lines 112–126 — `_parse_item_line`):
```python
def _parse_item_line(raw_line: str) -> ParsedItem:
    """Apply ITEM_RE to a single catalog item line. Falls back to name-only on no-match.

    Never raises. Unparseable lines are returned as name-only ParsedItems with
    raw_line preserved.
    """
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
Copy this never-raises / name-only fallback / `raw_line=raw_line` convention exactly into `_parse_markdown_row`. The new helper must also never raise; structural mismatches fall back to `ParsedItem(name=..., version=None, id=None, raw_line=row)`.

**State machine / public function pattern** (lines 134–234 — `parse_catalog`):
```python
def parse_catalog(path: Path) -> ParsedCatalog:
    path = Path(path)                          # accept both str and Path
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    catalog = ParsedCatalog(path=str(path))

    state = "SEEKING_TITLE"
    current_title: str | None = None
    current_items: list[ParsedItem] = []
    current_degraded: bool = False

    for line in lines:
        if state == "SEEKING_TITLE":
            ...
        elif state == "SEEKING_SEPARATOR":
            ...
        elif state == "COLLECTING":
            if line == "":
                # flush section
                catalog.sections.append(ParsedSection(...))
                ...
    # EOF flush
    if state == "COLLECTING" and current_title is not None:
        catalog.sections.append(...)

    return catalog
```
Copy these exact conventions into `parse_markdown_catalog`:
- `path = Path(path)` as the first statement (accepts both `str` and `Path`)
- `path.read_text(encoding="utf-8")` — same encoding
- `text.split("\n")` — same line splitting
- `ParsedCatalog(path=str(path))` — same path storage
- `catalog.sections.append(current_section)` flush at EOF
- Function raises `ValueError` (not `sys.exit`) for format errors — kept pure/testable

**Docstring convention** (lines 134–158):
```python
def parse_catalog(path: Path) -> ParsedCatalog:
    """Read a catalog file and return typed structured items.

    ...
    State machine states:
      SEEKING_TITLE     — scanning for a section title line
      ...
    EOF flush rule: ...
    """
```
`parse_markdown_catalog` should document its states (`IN_FRONTMATTER`, `BODY`) and its two `ValueError` cases in the docstring.

---

### `src/maccat/reinstall/cli.py` — `run_reinstall` update

**Analog:** `src/maccat/reinstall/cli.py` lines 54–82

**Deferred import pattern** (lines 54–57):
```python
# Deferred imports per PKG-03
from maccat.reinstall.emitter import emit_reinstall_script
from maccat.reinstall.parser import parse_catalog
from maccat.reinstall.picker import resolve_catalog_path
```
Change the `parse_catalog` import to `parse_markdown_catalog`. The deferred import block structure stays identical — add to the same block.

**Error handling pattern** (lines 64–72):
```python
# WR-01: parse_catalog -> Path.read_text can raise OSError ...
try:
    catalog = parse_catalog(catalog_path)
except OSError as exc:
    sys.exit(f"ERROR: Could not read catalog file {catalog_path}: {exc}")
```
Expand to:
```python
try:
    catalog = parse_markdown_catalog(catalog_path)
except (OSError, ValueError) as exc:
    sys.exit(f"ERROR: {exc}")
```
The `ValueError` message from `parse_markdown_catalog` is already self-contained and actionable (includes the `maccat convert --from PATH` directive), so `f"ERROR: {exc}"` is the correct pattern. The existing `OSError` message format (`f"ERROR: Could not read catalog file {catalog_path}: {exc}"`) is replaced; the new form delegates full message construction to the parser for both error types.

---

### `tests/reinstall/test_parser_contract.py` — new `TestMarkdownRoundTrip` and `TestMarkdownParserRefusal` classes

**Analog:** `tests/reinstall/test_parser_contract.py` — existing `TestRoundTrip` and `TestParseCatalog`

**Imports pattern** (lines 1–15):
```python
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.catalog.format import emit_item
from maccat.reinstall.parser import (
    _parse_item_line,
    parse_catalog,
)
```
Add to the import block:
```python
from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section
from maccat.reinstall.parser import parse_markdown_catalog
```

**Test data table pattern** (lines 22–32 — `ROUND_TRIP_CASES`):
```python
ROUND_TRIP_CASES = [
    ("Final Cut Pro", "10.7.1", "424389933", "Final Cut Pro", "10.7.1", "424389933"),
    ("Safari", "15.0", "", "Safari", "15.0", None),
    ...
]
```
Define a parallel `MARKDOWN_ROUND_TRIP_CASES` list of `(name, version, id_)` tuples covering all item shapes including adversarial values (pipe in name, backslash in name, both version and id, version only, id only, neither).

**`pytest.fixture()` returning a `Path` pattern** (lines 252–282 — `TestParseCatalog`):
```python
class TestParseCatalog:
    def test_two_section_catalog_returns_both_sections(self, tmp_path: Path) -> None:
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_TWO_SECTIONS, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 2
        assert result.sections[0].title == "Homebrew Packages"
```
`TestMarkdownRoundTrip` adds a `rendered_catalog` fixture that calls `render_markdown_catalog(sections, ...)`, writes the result to `tmp_path / "mac-software-list-[TestMac]-20260618123456.md"`, and returns `(sections, path)`. Each test method receives that fixture, calls `parse_markdown_catalog(path)`, and asserts the round-trip contract.

**`pytest.raises` pattern** (lines 183–195 — not present in this file; see `test_reinstall_cli.py` lines 182–184):
```python
with pytest.raises(SystemExit) as exc:
    run()
assert exc.value.code != 0
```
`TestMarkdownParserRefusal` uses `pytest.raises(ValueError, match="maccat convert --from")` for parser-level tests and `pytest.raises(SystemExit)` for the `run_reinstall` integration test. Copy the existing `pytest.raises` + `.code != 0` assertion structure.

**Fixture catalog string pattern** (lines 206–249):
```python
_CATALOG_TWO_SECTIONS = (
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "git (2.44.0)\n"
    ...
)
```
New markdown fixture strings follow the same parenthesized multi-line string convention with one string literal per logical line:
```python
_MINIMAL_MD_CATALOG = (
    '---\n'
    'computer: "TestMac"\n'
    'hostname: "test-mac.local"\n'
    'generated: "2026-06-18T12:34:56"\n'
    'maccat_version: "2.1.0"\n'
    '---\n'
    '# Installed Mac Software List\n'
    '\n'
    '## Homebrew Packages\n'
    '| Name | Version | ID |\n'
    '| --- | --- | --- |\n'
    '| wget | 1.21.3 |   |\n'
    '\n'
)
```

---

### `tests/reinstall/test_reinstall_cli.py` — fixture update

**Analog:** `tests/reinstall/test_reinstall_cli.py` lines 22–30 and 41–52

**`_MINIMAL_CATALOG` constant** (lines 22–30):
```python
_MINIMAL_CATALOG = (
    "Installed Mac Software List\n"
    "------------------------------------\n"
    "\n"
    "Homebrew Packages\n"
    "------------------------------------\n"
    "wget (1.21.3)\n"
    "\n"
)
```
Replace with:
```python
_MINIMAL_CATALOG = (
    '---\n'
    'computer: "TestMac"\n'
    'hostname: "test-mac.local"\n'
    'generated: "2026-06-18T12:34:56"\n'
    'maccat_version: "2.1.0"\n'
    '---\n'
    '# Installed Mac Software List\n'
    '\n'
    '## Homebrew Packages\n'
    '| Name | Version | ID |\n'
    '| --- | --- | --- |\n'
    '| wget | 1.21.3 |   |\n'
    '\n'
)
```

**`fixture_catalog` path** (line 50):
```python
catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
```
Change `.txt` → `.md`:
```python
catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.md"
```

**`test_gen_path_not_triggered_by_reinstall` glob assertion** (line 155):
```python
txt_files = list(output_dir.glob("mac-software-list-*.txt"))
assert len(txt_files) == 0, (
    f"No catalog .txt file should be written by reinstall; found: {txt_files}"
)
```
Change glob to `*.md`:
```python
md_files = list(output_dir.glob("mac-software-list-*.md"))
assert len(md_files) == 0, (
    f"No catalog .md file should be written by reinstall; found: {md_files}"
)
```

**`test_computer_flag_forwarded_to_picker` catalog write** (lines 293–295):
```python
catalog = computer_dir / make_catalog_filename("TestMac", "20260616120000")
catalog.write_text(_MINIMAL_CATALOG, encoding="utf-8")
```
After `_MINIMAL_CATALOG` becomes markdown content, this test will also need the fixture filename to be `.md` — `make_catalog_filename` already returns `.md` filenames after Phase 30, so this should be fine without further change.

**`test_picker_mode_writes_reinstall_sh_from_newest`** (lines 337–339):
```python
older = computer_dir / make_catalog_filename("PickedMac", "20260601120000")
newer = computer_dir / make_catalog_filename("PickedMac", "20260616120000")
older.write_text(_MINIMAL_CATALOG, encoding="utf-8")
newer.write_text(_MINIMAL_CATALOG, encoding="utf-8")
```
These use `_MINIMAL_CATALOG` — once that constant is updated to markdown content, both writes will produce valid `.md` catalogs. Confirm `make_catalog_filename` already returns `.md` (Phase 30 already changed this).

---

### `tests/reinstall/test_picker_and_reinstall_cli.py` — fixture update

**Analog:** `tests/reinstall/test_picker_and_reinstall_cli.py` lines 173–187

**`TestRunReinstall.fixture_catalog` content** (lines 176–186):
```python
content = (
    "Installed Mac Software List\n"
    "------------------------------------\n"
    "\n"
    "Homebrew Packages\n"
    "------------------------------------\n"
    "wget (1.21.3)\n"
    "\n"
)
catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
catalog.write_text(content, encoding="utf-8")
```
Replace `content` with the same `_MINIMAL_MD_CATALOG` string and change `.txt` → `.md`:
```python
content = (
    '---\n'
    'computer: "TestMac"\n'
    'hostname: "test-mac.local"\n'
    'generated: "2026-06-18T12:34:56"\n'
    'maccat_version: "2.1.0"\n'
    '---\n'
    '# Installed Mac Software List\n'
    '\n'
    '## Homebrew Packages\n'
    '| Name | Version | ID |\n'
    '| --- | --- | --- |\n'
    '| wget | 1.21.3 |   |\n'
    '\n'
)
catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.md"
catalog.write_text(content, encoding="utf-8")
```

---

## Shared Patterns

### `ValueError` → `sys.exit` conversion
**Source:** `src/maccat/reinstall/cli.py` lines 64–72
**Apply to:** `run_reinstall` (the only consumer of `parse_markdown_catalog`)
```python
try:
    catalog = parse_markdown_catalog(catalog_path)
except (OSError, ValueError) as exc:
    sys.exit(f"ERROR: {exc}")
```
Keep the parser raising `ValueError` (not calling `sys.exit`) so it is testable with `pytest.raises(ValueError)`.

### Path normalization at function entry
**Source:** `src/maccat/reinstall/parser.py` line 161
**Apply to:** `parse_markdown_catalog`
```python
path = Path(path)
```
Place this as the first statement in `parse_markdown_catalog` — mirrors `parse_catalog` and makes the function accept both `str` and `Path`.

### UTF-8 file reads
**Source:** `src/maccat/reinstall/parser.py` line 162
**Apply to:** `parse_markdown_catalog`
```python
text = path.read_text(encoding="utf-8")
```
Always explicit — no reliance on locale default.

### Deferred imports (PKG-03)
**Source:** `src/maccat/reinstall/cli.py` lines 54–57
**Apply to:** `run_reinstall` import block
```python
from maccat.reinstall.parser import parse_markdown_catalog
```
Replace the existing `parse_catalog` import with `parse_markdown_catalog` in the same deferred block. Do not add a top-level import.

### Never-raise item-level helpers
**Source:** `src/maccat/reinstall/parser.py` lines 112–126 (`_parse_item_line`)
**Apply to:** `_parse_markdown_row`
```python
# Never raises. On structural mismatch, returns ParsedItem(name=..., version=None, id=None, raw_line=row)
```
Item-level helpers in this module must not raise. Propagate `OSError` from `path.read_text` only. All other malformation → fallback `ParsedItem`.

### `ParsedItem.raw_line` = the source line string
**Source:** `src/maccat/reinstall/parser.py` line 125 (`raw_line=raw_line`)
**Apply to:** `_parse_markdown_row`
```python
return ParsedItem(name=name, version=version, id=id_, raw_line=row)
```
`raw_line` is always the actual source string read from the file (`row` = the table row string `| name | ver | id |`), not a reconstructed form.

### `catalog.sections.append` EOF flush
**Source:** `src/maccat/reinstall/parser.py` lines 224–232
**Apply to:** `parse_markdown_catalog` (after the for-loop)
```python
if current_section is not None:
    catalog.sections.append(current_section)
```
Always flush the in-progress section after the loop ends.

---

## Emitter Format Reference (for parser inverse)

**Source:** `src/maccat/catalog/markdown.py`

**`_escape_cell`** (lines 76–83):
```python
def _escape_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", r"\|")
```
Inverse (`_unescape_cell`): strip surrounding whitespace, then `s.replace("\\|", "|").replace("\\\\", "\\")`. Either unescape order is mathematically correct for this escape scheme.

**Table row format** (`_render_table`, line 118):
```python
rows.append(f"| {_escape_cell(name)} | {ver_cell} | {id_cell} |")
```
Column separator is always ` | ` (space-pipe-space). Strip leading `| ` and trailing ` |`, then `split(" | ")` on the inner string.

**Empty cell** (`_render_table`, lines 116–117):
```python
ver_cell = _escape_cell(version) if version else " "
id_cell = _escape_cell(id_) if id_ else " "
```
Empty version/id renders as a single space `" "`. After `split(" | ")` the cell value is `" "` → `strip()` → `""` → map to `None`.

**`(none found)` sentinel** (`render_markdown_catalog`, lines 195–205):
```python
parts.append("(none found)\n")
```
No leading spaces (unlike the legacy `NONE_FOUND_SENTINEL = "  (none found)"`). The parser line for this is `line == "(none found)"` (exact match).

**Frontmatter structure** (`render_frontmatter`, lines 139–145):
```python
return (
    "---\n"
    f"computer: {_yaml_quote(computer)}\n"
    f"hostname: {_yaml_quote(hostname)}\n"
    f"generated: {_yaml_quote(generated)}\n"
    f"maccat_version: {_yaml_quote(maccat_version)}\n"
    "---\n"
)
```
Validation: `lines[0] == "---"` opens; first subsequent `lines[i] == "---"` closes. No PyYAML needed — treat frontmatter as opaque lines.

---

## No Analog Found

All files in scope have close analogs. No entries.

---

## Metadata

**Analog search scope:** `src/maccat/reinstall/`, `src/maccat/catalog/`, `tests/reinstall/`
**Files scanned:** 5 (all read in full — all under 350 lines)
**Pattern extraction date:** 2026-06-18
