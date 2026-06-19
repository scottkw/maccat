---
phase: "30-markdown-emitter-md-plumbing"
plan: 1
subsystem: "catalog/markdown"
tags: [markdown, emitter, formatter, tdd]
dependency_graph:
  requires: []
  provides:
    - "render_markdown_catalog(sections, *, computer, hostname, generated, maccat_version) -> str"
    - "CatalogWriter.write_raw(content: str) -> None"
  affects:
    - "src/maccat/catalog/writer.py"
tech_stack:
  added: []
  patterns:
    - "Pure-function emitter (no I/O, returns str)"
    - "TDD RED/GREEN/REFACTOR"
    - "Duplicate constants to avoid cross-module coupling"
key_files:
  created:
    - path: "src/maccat/catalog/markdown.py"
      role: "Pure markdown emitter — render_markdown_catalog, render_frontmatter, _render_table, _parse_columns, _escape_cell"
    - path: "tests/test_markdown_emitter.py"
      role: "Unit test suite — 8 test classes, 52 tests"
  modified:
    - path: "src/maccat/catalog/writer.py"
      role: "Added write_raw(content: str) method"
decisions:
  - "Duplicated _ITEM_RE and _DEGRADATION_LINES from reinstall/parser.py to avoid coupling to the reinstall module"
  - "Empty cell convention: single space ' ' for missing version/id per CONTEXT.md"
  - "(none found) written without leading spaces — markdown plain line, not two-space-indented plain-text convention"
  - "TestWriteRaw added as Task 2 covers write_raw; tests live in test_markdown_emitter.py alongside the emitter tests"
metrics:
  duration: "4 minutes"
  completed: "2026-06-18"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 30 Plan 1: Markdown Emitter Core Summary

**One-liner:** YAML-frontmatter + 3-column Name|Version|ID markdown emitter using duplicated ITEM_RE regex, flush_section delegation for sort, and pipe-escape safety.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for render_markdown_catalog | ef80bc7 | tests/test_markdown_emitter.py |
| 1 (GREEN) | Create catalog/markdown.py | 6299deb | src/maccat/catalog/markdown.py |
| 2 (GREEN) | Add write_raw to CatalogWriter | c2e2529 | src/maccat/catalog/writer.py |

## What Was Built

### `src/maccat/catalog/markdown.py` (new)

Pure formatting module — no file I/O, no subprocess calls beyond the flush_section delegation.

- `render_frontmatter(computer, hostname, generated, maccat_version)` — YAML frontmatter block with fixed key order (computer/hostname/generated/maccat_version) and double-quoted `generated` to prevent YAML 1.1 datetime auto-cast.
- `_escape_cell(value)` — replaces `|` with `\|` before cell insertion.
- `_parse_columns(line)` — applies `_ITEM_RE`; returns `(name, version, id_)`, falls back to `(line, "", "")` on no match; never raises.
- `_render_table(items)` — 3-column header + separator + one row per item; missing version/id renders as `" "` (single space).
- `render_markdown_catalog(sections, *, computer, hostname, generated, maccat_version)` — builds frontmatter + title + per-section `## heading` + table-or-(none found). Non-raw path: `flush_section()` for sort+dedup. Raw path: preserves collector order, checks for degradation lines.

**Duplicated from reinstall/parser.py:**
- `_ITEM_RE` — right-anchored alternation for all 6 emit_item shapes + Homebrew multi-version
- `_DEGRADATION_LINES` — frozenset of 5 degradation strings

### `src/maccat/catalog/writer.py` (modified)

Added `write_raw(self, content: str) -> None`:
- Same `assert self._fh is not None` guard pattern as `write_lines` and `write_section`
- Writes content in a single call (no per-line newline added — caller's responsibility)

### `tests/test_markdown_emitter.py` (new)

8 test classes, 52 tests covering all plan behavior:

| Class | What It Tests |
|-------|--------------|
| TestFrontmatter | Key order, double-quoting of generated, fences, maccat_version bare scalar |
| TestTableRendering | Header/separator rows, all 10 item shapes (parametrized), empty cells |
| TestPipeEscaping | `\|` escaping in name/id cells, row structure integrity |
| TestEmptySections | (none found) for empty items, no table header, raw+non-raw paths |
| TestDegradedSections | All 5 degradation lines -> (none found), no table rows |
| TestRawVsNonRaw | raw=True preserves order, raw=False applies flush_section, dedup |
| TestDeterminism | Byte-identical output with fixed timestamp |
| TestWriteRaw | write_raw writes content, assert guard, atomic on exception |

## Deviations from Plan

None — plan executed exactly as written.

The only structural note: the plan listed `tests/test_markdown_emitter.py` as a Task 2 output, but TDD requires failing tests before implementation. The test file was created in the Task 1 RED phase (covering all behavior for both tasks), then committed green across both tasks. This is consistent with the TDD protocol.

## Known Stubs

None — all behavior fully implemented and tested.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes. The markdown emitter is a pure string transformation; it re-parses already-clean collector item strings downstream of the FMT-03 invariant.

## Self-Check: PASSED

Files exist:
- src/maccat/catalog/markdown.py: FOUND
- src/maccat/catalog/writer.py (write_raw): FOUND
- tests/test_markdown_emitter.py: FOUND

Commits exist:
- ef80bc7: FOUND (test RED)
- 6299deb: FOUND (feat markdown.py)
- c2e2529: FOUND (feat write_raw)
