---
phase: 15-collectors
plan: "07"
subsystem: collectors
tags: [vscode, cursor, extensions, subprocess, nls, rsplit]

# Dependency graph
requires:
  - phase: 15-collectors/15-01
    provides: Collector ABC, Section, CollectorResult base types
  - phase: 13-package-foundation-output-format
    provides: emit_item, flush_section, resolve_vsc_ext_name helper

provides:
  - VSCodeCollector: CLI-preferred + extensions.json fallback for ~/.vscode/extensions
  - CursorCollector: thin wrapper over shared helper for ~/.cursor/extensions
  - _collect_editor_extensions: shared module-level helper in vscode.py

affects: [15-08, collectors/__init__.py registry, Phase 16 CLI integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-path CLI/file-fallback: try subprocess CLI first, fall back to extensions.json"
    - "rsplit('@', 1) for last-@ split mirroring zsh \${line%@*}/\${line##*@}"
    - "relativeLocation absent -> display_name = id_ (Pitfall D: no bad path to resolve_vsc_ext_name)"
    - "Thin-wrapper collector: CursorCollector imports _collect_editor_extensions from vscode.py"

key-files:
  created:
    - src/maccat/collectors/vscode.py
    - src/maccat/collectors/cursor.py
    - tests/collectors/test_vscode.py
    - tests/collectors/test_cursor.py
  modified: []

key-decisions:
  - "CursorCollector is a pure thin wrapper: all logic in _collect_editor_extensions in vscode.py; cursor.py has no duplicate logic"
  - "relativeLocation absent in extensions.json -> display_name = id_ directly, no resolve_vsc_ext_name call with invalid path (Pitfall D)"
  - "rsplit('@', 1) mandatory: publisher IDs can contain @ characters; always split on the last @ only"
  - "NOTE message to stderr (not catalog) when CLI absent and no extensions.json; WARNING to stderr when CLI present but empty"

patterns-established:
  - "Two-path CLI/file-fallback pattern: Path A (CLI) preferred; Path B (extensions.json) when CLI absent or returns empty"
  - "Module-level shared helper (_collect_editor_extensions) imported by thin wrapper collectors to eliminate logic duplication"

requirements-completed: [CAT-01, CAT-06]

# Metrics
duration: 4min
completed: 2026-06-15
---

# Phase 15 Plan 07: VSCodeCollector + CursorCollector Summary

**VSCodeCollector and CursorCollector using CLI-preferred/extensions.json-fallback two-path pattern with rsplit('@',1) last-@ split and NLS display name resolution via resolve_vsc_ext_name.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-15T01:03:53Z
- **Completed:** 2026-06-15T01:07:14Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Implemented `_collect_editor_extensions` shared helper in vscode.py covering Path A (CLI `--list-extensions --show-versions`) and Path B (extensions.json fallback), with `rsplit('@', 1)` last-@ parsing mirroring zsh `${line%@*}`/`${line##*@}`
- VSCodeCollector delegates to the shared helper for `~/.vscode/extensions`; CursorCollector is a one-method thin wrapper delegating to the same helper for `~/.cursor/extensions`
- 14 new unit tests covering CLI path, NLS display name resolution, rsplit last-@ correctness, malformed line skip, CLI-empty fallback with WARNING, absent-both fallback with NOTE, and section structure invariants (title, raw=False)

## Task Commits

1. **Task 1: VSCodeCollector, _collect_editor_extensions helper, and CursorCollector** - `963aff9` (feat)
2. **Task 2: Unit tests for VSCodeCollector and CursorCollector** - `2ca56bf` (test)

## Files Created/Modified

- `/Users/ken/dev/mac-software-list/src/maccat/collectors/vscode.py` - VSCodeCollector + _collect_editor_extensions shared helper (155 lines)
- `/Users/ken/dev/mac-software-list/src/maccat/collectors/cursor.py` - CursorCollector thin wrapper (31 lines)
- `/Users/ken/dev/mac-software-list/tests/collectors/test_vscode.py` - 9 VSCodeCollector behaviors (165 lines)
- `/Users/ken/dev/mac-software-list/tests/collectors/test_cursor.py` - 5 CursorCollector behaviors (96 lines)

## Decisions Made

- CursorCollector is a pure thin wrapper — all logic lives in `_collect_editor_extensions` in vscode.py; cursor.py imports the helper rather than duplicating it
- `relativeLocation` absent in extensions.json → `display_name = id_` directly with no `resolve_vsc_ext_name` call (Pitfall D: avoids calling name resolver with a non-existent path)
- `rsplit('@', 1)` is mandatory because VS Code extension IDs themselves can contain `@` characters; always split on the last `@` only
- stderr messages (NOTE/WARNING) go to `sys.stderr` not to the catalog output, matching zsh behavior

## Deviations from Plan

None — plan executed exactly as written.

The plan's PATTERNS.md pattern had a slight discrepancy in the Path B "CLI present but returned empty" warning message format vs. what the plan spec said. I used the spec from the plan's `<action>` block (`WARNING: {cli_name} CLI returned empty list`) rather than the PATTERNS.md variant (which dropped `WARNING:`). The `<action>` block is authoritative.

## Issues Encountered

Minor ruff violations on test files (import ordering, line length, unused imports from plan template). All fixed inline before commit.

## Next Phase Readiness

- Plan 15-08 (ChromeCollector + FirefoxCollector) is the only remaining plan in Phase 15
- `__init__.py` lazy `get_registry()` will pick up VSCodeCollector and CursorCollector automatically when they are registered

---
*Phase: 15-collectors*
*Completed: 2026-06-15*

## Self-Check: PASSED

- `src/maccat/collectors/vscode.py` FOUND
- `src/maccat/collectors/cursor.py` FOUND
- `tests/collectors/test_vscode.py` FOUND
- `tests/collectors/test_cursor.py` FOUND
- Commit `963aff9` FOUND
- Commit `2ca56bf` FOUND
