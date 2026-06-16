---
phase: 24-catalog-format-fix-parser-foundation
plan: "01"
subsystem: collectors/mas
tags: [mas, emit_item, catalog-format, MAS-01]
dependency_graph:
  requires: []
  provides: [mas-id-in-catalog]
  affects: [src/maccat/collectors/mas.py, tests/collectors/test_homebrew.py]
tech_stack:
  added: []
  patterns: [deferred-import-inside-method, emit_item-routing]
key_files:
  created: []
  modified:
    - src/maccat/collectors/mas.py
    - tests/collectors/test_homebrew.py
decisions:
  - "Deferred import of emit_item inside _parse_mas_output method body (established circular-import guard pattern)"
  - "Strip version parens with [1:-1] slice (not .strip) to avoid double-unstripping on malformed input"
  - "Retired awk-parity trailing-space behavior (WR-02) — no parity suite to break after v2.0.0 retirement"
metrics:
  duration: "~8 min"
  completed: "2026-06-16"
  tasks_completed: 2
  files_modified: 2
---

# Phase 24 Plan 01: MAS Collector Three-Column Parser Summary

Rewrote `MasCollector._parse_mas_output` to extract all three `mas list` columns (numeric id, multi-word name, paren-version) and route each entry through `emit_item(name, version, id_)`, producing `AppName (version) [id]` lines so the Phase 25 emitter can generate `mas install <id>` commands.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Rewrite _parse_mas_output in mas.py | c2cd4e6 | src/maccat/collectors/mas.py |
| 2 | Update TestMasCollector assertions in test_homebrew.py | 8fdd4e2 | tests/collectors/test_homebrew.py |

## What Was Built

**`src/maccat/collectors/mas.py` — `_parse_mas_output` rewritten:**
- Extracts `id_` from `parts[0]` (numeric App Store ID, previously skipped)
- Joins `parts[1:-1]` for multi-word app names (previously truncated at `parts[1]`)
- Strips version parens with `last[1:-1]` (not `.strip("()")`) to avoid double-stripping
- Routes each entry through `emit_item(name, version, id_)` for FMT-01 compliance
- Deferred import `from maccat.catalog.format import emit_item` inside method body (established circular-import guard)
- 2-field lines (no version) produce `"AppName [id]"` instead of `"AppName "` (trailing space)
- Class docstring updated: removed awk-equivalence paragraph, added MAS-01 note

**`tests/collectors/test_homebrew.py` — two targeted changes:**
- `test_mas_collect_parses_output`: docstring and assertion updated to `["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]`
- `test_mas_two_field_line_emits_trailing_space` replaced with `test_mas_two_field_line_degrades_to_name_id`: asserts `["OnlyTwo [123]", "Safari (15.0) [456]"]`

## Verification Results

```
pytest tests/ -x -q      → 421 passed, 5 skipped
ruff check mas.py + test  → All checks passed
mypy mas.py               → Success: no issues found in 1 source file
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The only trust boundary (mas CLI stdout → _parse_mas_output) was pre-existing and accepted per the plan's threat register (T-24-01-01).

## Self-Check: PASSED

- `src/maccat/collectors/mas.py` exists and contains `from maccat.catalog.format import emit_item`
- `tests/collectors/test_homebrew.py` contains `Safari (15.0) [1234567890]` and `test_mas_two_field_line_degrades_to_name_id`
- `tests/collectors/test_homebrew.py` does NOT contain `trailing_space`
- Commits c2cd4e6 and 8fdd4e2 verified in git log
- Full suite: 421 passed, 5 skipped
