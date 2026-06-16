---
phase: 02-editor-collectors
plan: 02-02
subsystem: self-test
tags: [zsh, self-test, vscode, cursor, nls, determinism, ephemeral]
dependency_graph:
  requires: [02-01]
  provides: [phase-02-verified]
  affects: []
tech_stack:
  added: []
  patterns: [ephemeral-self-test, awk-extraction, stub-OUTPUT_FILE]
key_files:
  created: []
  modified: []
decisions:
  - "grep -c exits 1 on zero-match count; use `; true` (not `|| echo 0`) to capture the count without triggering fallback echo duplication"
  - "Ephemeral test script cleans itself up on success (rm -f /tmp/gsd-phase2-test.zsh at end)"
  - "Harness extracts lines 254-924 via awk NR range (write_section through collect_cursor_extensions, before MAIN block at line 925)"
metrics:
  duration_minutes: 1
  completed_date: "2026-06-13"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 0
---

# Phase 02 Plan 02: Phase 2 Self-Test Summary

**One-liner:** Ephemeral Zsh self-test (15 assertions, 9 groups A–I) confirms resolve_vsc_ext_name NLS resolution and both collectors produce correct real-data output, with no %key% leakage and byte-identical determinism.

## What Was Built

An ephemeral test script at `/tmp/gsd-phase2-test.zsh` (never committed) exercising:

- `resolve_vsc_ext_name` with 5 synthetic fixture cases (groups A–E)
- `collect_vscode_extensions` against real `~/.vscode/extensions/extensions.json` (group F)
- `collect_cursor_extensions` against real `~/.cursor/extensions/extensions.json` (group G)
- Missing `package.json` fallback behavior (group H)
- Two-run determinism for both collectors (group I)

The harness extracts lines 254–924 of `update-list.sh` via `awk NR>=254 && NR<=924` into
`/tmp/gsd-phase2-helpers.zsh`, stubs `OUTPUT_FILE` and `_section_lines=()`, and sources
the extracted file. This isolates the helper and collector functions from the script's main
block, which starts at line 925.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write and run ephemeral self-test for Phase 2 collectors | (no commit — ephemeral) | /tmp/gsd-phase2-test.zsh |

## Self-Test Results

All 15 assertions across 9 test groups passed:

- **A (plain displayName):** `resolve_vsc_ext_name` returns the plain string unchanged
- **B (missing displayName):** falls back to the extension ID with no blank/crash
- **C (%displayName% NLS):** `%displayName%` placeholder resolved to "HTML Preview" via `package.nls.json`
- **D (dotted NLS key):** `%extension.title%` (literal-dot key) resolved to "IntelliCode API Usage Examples" — confirms `.[$k]` not `getpath` is in use
- **E (missing nls file):** returns extension ID without abort
- **F (VS Code real data):** section header present; 22 entries in `name (version) [id]` format; "Auto Rename Tag (0.1.10) [formulahendry.auto-rename-tag]" verified; zero raw `%key%` strings
- **G (Cursor real data):** section header present; 47 entries in format; zero raw `%key%` strings
- **H (missing package.json):** `resolve_vsc_ext_name` returns ID fallback, run continues
- **I (determinism):** two consecutive VS Code runs and two consecutive Cursor runs both produce empty diff

## Deviations from Plan

**1. [Rule 1 - Bug] `grep -c` exit-code / `|| echo 0` double-zero output**

- **Found during:** Task 1, first run (F4 and G3 FAILed)
- **Issue:** `grep -cE '%[A-Za-z]'` exits with code 1 when it finds zero matches (POSIX behavior). The plan's suggested `|| echo 0` guard then appended a second "0" to the count output, producing `"0\n0"` — which did not equal the expected `"0"`.
- **Fix:** Replaced `|| echo 0` with `; true` (which does not trigger on non-zero exit) and added `raw_pct="${raw_pct%%$'\n'*}"` to trim any trailing newline artifacts.
- **Files modified:** /tmp/gsd-phase2-test.zsh only (ephemeral; not committed)
- **Impact:** None on update-list.sh. The production code never uses `grep -c` for this purpose.

## Post-Test State Verification

- `update-list.sh` has no uncommitted modifications: VERIFIED (`git status --short update-list.sh` is clean)
- `zsh -n update-list.sh` exits 0: VERIFIED
- Ephemeral files cleaned up: VERIFIED (test script self-deletes on success; /tmp/gsd-p2-* fixtures removed)

## Known Stubs

None. The collectors produce real output from live extension data on this machine.

## Threat Flags

None. The self-test reads only local files under `/tmp` (fixtures) and `~/.vscode/extensions` / `~/.cursor/extensions` (read-only). No new network endpoints, auth paths, or trust-boundary schema changes introduced.

## Self-Check: PASSED

- All 15 assertions pass (0 FAIL): VERIFIED
- "ALL TESTS PASSED" printed; exit code 0: VERIFIED
- update-list.sh unmodified: VERIFIED
- No committed files from this plan: VERIFIED
- zsh -n update-list.sh exits 0: VERIFIED
