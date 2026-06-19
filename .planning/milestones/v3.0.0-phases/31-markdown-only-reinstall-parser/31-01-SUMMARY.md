---
phase: 31-markdown-only-reinstall-parser
plan: "01"
subsystem: reinstall/parser
tags: [parser, markdown, round-trip, tdd, ruledev]
dependency_graph:
  requires:
    - "30-02: markdown emitter (render_markdown_catalog) — format anchor"
  provides:
    - "parse_markdown_catalog(path) -> ParsedCatalog — Phase 32 convert reads .txt via parse_catalog and writes .md; reinstall now reads .md via parse_markdown_catalog"
  affects:
    - "reinstall pipeline: run_reinstall now calls parse_markdown_catalog instead of parse_catalog"
    - "test fixtures: test_reinstall_cli.py + test_picker_and_reinstall_cli.py updated to .md format"
tech_stack:
  added: []
  patterns:
    - "State-machine line iterator with frontmatter-skip phase (same pattern as parse_catalog)"
    - "Never-raises item-level helper with name-only fallback (mirrors _parse_item_line)"
    - "ValueError → sys.exit in CLI (same pattern as OSError; keeps parser pure/testable)"
key_files:
  created: []
  modified:
    - src/maccat/reinstall/parser.py
    - src/maccat/reinstall/cli.py
    - tests/reinstall/test_parser_contract.py
    - tests/reinstall/test_reinstall_cli.py
    - tests/reinstall/test_picker_and_reinstall_cli.py
decisions:
  - "MD_NONE_FOUND = '(none found)' (no leading spaces) — distinct from NONE_FOUND_SENTINEL '  (none found)' (two spaces, legacy format); both coexist in parser.py"
  - "Unescape order: pipe first (\\| → |) then backslash (\\\\ → \\) — either order is mathematically correct; pipe-first chosen by convention"
  - "(none found) in markdown → items=[], degraded=False — the emitter already converts degraded sections to (none found), so the markdown parser cannot and need not distinguish them"
  - "ValueError (not sys.exit) raised by parse_markdown_catalog — keeps parser pure/testable; cli.py catches it alongside OSError"
  - "Split on ' | ' (space-pipe-space) after stripping row[2:-2] — correct because _escape_cell converts bare | to \\|, which can never produce space-pipe-space in a cell value"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-18"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
  tests_added: 13
  tests_total: 140
---

# Phase 31 Plan 01: Markdown-Only Reinstall Parser Summary

Lossless markdown catalog parser (`parse_markdown_catalog`) added to `reinstall/parser.py`, inverting Phase 30's `render_markdown_catalog` emitter. The `maccat reinstall` pipeline is rewired to the markdown format; a round-trip contract test locks emitter ↔ parser at the file level for all item shapes including adversarial cell values (pipe, backslash, empty cells).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add parse_markdown_catalog and helpers to parser.py | 0e88146 | src/maccat/reinstall/parser.py |
| 2 | Add TestMarkdownRoundTrip + TestMarkdownParserRefusal; wire cli.py | 2cf0e46 | tests/reinstall/test_parser_contract.py, src/maccat/reinstall/cli.py, tests/reinstall/test_reinstall_cli.py, tests/reinstall/test_picker_and_reinstall_cli.py |
| — | Remove TDD RED gate file | 3907b16 | tests/reinstall/test_markdown_parser_red.py (deleted) |

## What Was Built

### `src/maccat/reinstall/parser.py` — new additions (legacy code untouched)

- `MD_NONE_FOUND = "(none found)"` — no leading spaces; distinct from `NONE_FOUND_SENTINEL` which has two leading spaces for the legacy format
- `_unescape_cell(value: str) -> str` — strips surrounding whitespace, then unescapes `\|` → `|` and `\\` → `\`; inverse of `_escape_cell` from `catalog/markdown.py`
- `_parse_markdown_row(row: str) -> ParsedItem | None` — strips `| ` and ` |` from row ends, splits inner content on ` | `, maps empty cells to None, returns name-only `ParsedItem` on structural mismatch; never raises
- `parse_markdown_catalog(path: Path) -> ParsedCatalog` — validates `.md` extension and opening `---` fence, finds closing `---`, then iterates body lines for `## sections` and `| table rows |`; raises `ValueError` with `maccat convert --from` in the message for invalid inputs

### `src/maccat/reinstall/cli.py`

Replaced `parse_catalog` import+call with `parse_markdown_catalog`; expanded `except OSError` to `except (OSError, ValueError)`. The `ValueError` message from `parse_markdown_catalog` is self-contained and actionable, so `f"ERROR: {exc}"` is the correct delegation pattern.

### `tests/reinstall/test_parser_contract.py`

Added `TestMarkdownRoundTrip` (9 tests) and `TestMarkdownParserRefusal` (4 tests) alongside the existing legacy parser tests. The `rendered_catalog` fixture calls `render_markdown_catalog` → writes to disk → calls `parse_markdown_catalog`, asserting losslessness across all item shapes.

### Fixture updates (deviations)

`test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py`: `_MINIMAL_CATALOG` updated to markdown format, fixture paths `.txt` → `.md`, glob assertion `.txt` → `.md`. Required because `run_reinstall` now calls `parse_markdown_catalog` which refuses `.txt` files.

## Deviations from Plan

### Auto-added — Rule 2 (Missing Critical Functionality)

**1. [Rule 2 - Missing] Wire cli.py to parse_markdown_catalog**
- **Found during:** Task 2 RED phase — `test_run_reinstall_exits_nonzero_on_txt` failed because `run_reinstall` still called `parse_catalog`
- **Fix:** Replace `from maccat.reinstall.parser import parse_catalog` with `parse_markdown_catalog`; expand `except OSError` to `except (OSError, ValueError)` in `run_reinstall`
- **Files modified:** `src/maccat/reinstall/cli.py`
- **Commit:** 2cf0e46
- **Note:** The RESEARCH.md File Change Inventory listed `cli.py` as a required change; the PLAN.md `files_modified` list omitted it but the plan's RIN-02 requirement and Task 2's `test_run_reinstall_exits_nonzero_on_txt` test both require it

**2. [Rule 2 - Missing] Update test_reinstall_cli.py fixture from .txt to .md**
- **Found during:** Task 2 implementation — after cli.py update, existing `.txt` fixture caused `test_from_path_writes_reinstall_sh` to fail with SystemExit
- **Fix:** Updated `_MINIMAL_CATALOG` to markdown content, fixture filename `.txt` → `.md`, glob assertion `.txt` → `.md`
- **Files modified:** `tests/reinstall/test_reinstall_cli.py`
- **Commit:** 2cf0e46

**3. [Rule 2 - Missing] Update test_picker_and_reinstall_cli.py fixture from .txt to .md**
- **Found during:** Task 2 implementation — same root cause as above
- **Fix:** Updated `TestRunReinstall.fixture_catalog` content and filename `.txt` → `.md`
- **Files modified:** `tests/reinstall/test_picker_and_reinstall_cli.py`
- **Commit:** 2cf0e46

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test(31-01)) | — | Implemented as `tests/reinstall/test_markdown_parser_red.py` (temp file, later removed) |
| GREEN (feat(31-01)) | 0e88146, 2cf0e46 | PASS — all 13 new tests pass |
| REFACTOR | — | Not required; code is clean |

Note: The TDD RED gate test file (`test_markdown_parser_red.py`) was created as a temp file (12 failing tests), then the GREEN implementation was added to `parser.py`, and finally the full test suite was written in `test_parser_contract.py` (Task 2). The RED file was removed in commit 3907b16.

## Verification Results

```
./venv/bin/pytest tests/reinstall/ -q  → 140 passed
./venv/bin/ruff check src/maccat/reinstall/parser.py tests/reinstall/test_parser_contract.py → All checks passed!
./venv/bin/mypy --strict src/maccat/reinstall/parser.py → Success: no issues found in 1 source file
```

- `from maccat.reinstall.parser import parse_catalog` → ok (legacy parser unchanged)
- `from maccat.reinstall.parser import parse_markdown_catalog` → ok
- `MD_NONE_FOUND == "(none found)"` → confirmed (no leading spaces)
- `NONE_FOUND_SENTINEL == "  (none found)"` → unchanged (two leading spaces)
- `TestMarkdownRoundTrip` (9 tests): all green
- `TestMarkdownParserRefusal` (4 tests): all green

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns beyond what was already in the plan's threat model, or schema changes introduced. The `parse_markdown_catalog` function reads user-controlled `.md` files via `Path.read_text` — same trust boundary as `parse_catalog`. All threat mitigations in the plan's `<threat_model>` are implemented:

- **T-31-01 (Tampering):** Implemented — `split(" | ")` after `row[2:-2]`; `len(cols) != 3` → name-only fallback
- **T-31-02 (ReDoS):** Not applicable — no regex used in markdown parser; all string methods
- **T-31-SC (Package installs):** Not applicable — stdlib-only, no new packages

## Self-Check: PASSED

All created/modified files exist and commits are present.
