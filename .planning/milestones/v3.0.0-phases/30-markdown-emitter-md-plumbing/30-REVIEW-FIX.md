---
phase: 30-markdown-emitter-md-plumbing
fixed_at: 2026-06-18T00:00:00Z
review_path: .planning/phases/30-markdown-emitter-md-plumbing/30-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 30: Code Review Fix Report

**Fixed at:** 2026-06-18
**Source review:** .planning/phases/30-markdown-emitter-md-plumbing/30-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: YAML frontmatter injection — unquoted `computer` and `hostname` scalars

**Files modified:** `src/maccat/catalog/markdown.py`, `tests/test_markdown_emitter.py`
**Commit:** d4cb62c
**Applied fix:**
- Added `_yaml_quote(value: str) -> str` helper that wraps a value in double quotes and escapes embedded backslashes (`\` → `\\`) and double-quotes (`"` → `\"`).
- Applied `_yaml_quote()` to all four frontmatter scalar values: `computer`, `hostname`, `generated`, and `maccat_version`.
- Updated module-level docstring format contract to show all values double-quoted.
- Updated `render_frontmatter()` docstring to explain the all-scalars-quoted policy.
- Updated tests: `test_computer_value_present` and `test_hostname_value_present` now assert quoted form; `test_maccat_version_bare_scalar` renamed to `test_maccat_version_double_quoted` asserting the quoted form.
- Added regression tests: `test_computer_with_colon_produces_valid_yaml`, `test_hostname_with_colon_produces_valid_yaml`, `test_computer_embedded_double_quote_escaped`.

### WR-01: `_escape_cell` does not escape backslash before pipe

**Files modified:** `src/maccat/catalog/markdown.py`, `tests/test_markdown_emitter.py`
**Commit:** b9b17a5
**Applied fix:**
- Changed `_escape_cell` to escape backslash before pipe: `value.replace("\\", "\\\\").replace("|", r"\|")`.
- Updated docstring to describe both escaping steps and explain ordering constraint.
- Added regression tests: `test_backslash_in_cell_is_escaped` (verifies `a\b` renders as `a\\b`) and `test_backslash_pipe_in_cell_does_not_split_column` (verifies `a\|b` produces exactly one data row with intact table structure).

### WR-02: Stale `.txt` extension in `CatalogWriter` docstring

**Files modified:** `src/maccat/catalog/writer.py`
**Commit:** d41b2af
**Applied fix:** Updated the `Usage::` example from `CatalogWriter(Path("MyMac/catalog-2026.txt"))` to `CatalogWriter(Path("MyMac/mac-software-list-[MyMac]-20260618120000.md"))`, matching the canonical naming convention and making the example round-trip through `parse_catalog_filename`.

### IN-01: `prune_old_archives` prints a spurious message on normal first run

**Files modified:** `src/maccat/retention.py`
**Commit:** c25cd48
**Applied fix:** Replaced `print("  No archive directory found — nothing to prune.")` followed by `return` with a silent `return  # normal: no archives yet — not an error condition`. The no-archive case is expected steady-state on first run and before any catalog has aged past the retention threshold; it does not merit output.

## Skipped Issues

None — all findings were fixed.

---

_Fixed: 2026-06-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
