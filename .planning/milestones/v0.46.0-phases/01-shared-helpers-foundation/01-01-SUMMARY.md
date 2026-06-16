---
phase: 01-shared-helpers-foundation
plan: 01-01
subsystem: shared-helpers
tags: [zsh, helpers, json, chrome, formatting, determinism]
dependency_graph:
  requires: []
  provides: [json_get, chrome_ext_name, emit_item, flush_section]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [jq→plutil-fallback, _section_lines-buffer, LC_ALL=C-sort-dedupe]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - "json_get uses jq → plutil fallback chain (no python3 — xcrun stub blocks on clean macOS)"
  - "chrome_ext_name falls back to 32-char extension ID when __MSG_ resolution fails (CHR-01)"
  - "emit_item covers 7 FMT-01 degradation cases; uses ID as name when name is absent to avoid id [id] duplication"
  - "_section_lines is a script-global array; collectors must reset _section_lines=() at their top as defensive pattern"
  - "flush_section uses LC_ALL=C sort -f -u for byte-stable, case-insensitive, deduplicated output (FMT-04)"
metrics:
  duration_minutes: 2
  completed_date: "2026-06-13"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 01 Plan 01: Shared Helpers Foundation Summary

**One-liner:** Four Zsh helper functions (json_get, chrome_ext_name, emit_item, flush_section) inserted into update-list.sh using jq→plutil fallback, __MSG__ locale resolution, FMT-01 7-case degradation, and LC_ALL=C sort -f -u deterministic output.

## What Was Built

Inserted 217 lines of Zsh helper code into `update-list.sh` between `write_section` (line 257) and `generate_catalog` (line 488). These four functions are the shared primitives every Phase 2–4 collector will call:

- **json_get(file, key):** Extracts a scalar JSON value by dotted key path. Backend chain: jq (Homebrew, optional) → plutil (always present on macOS since 10.4). Returns empty string on miss, missing file, or error. Handles nested paths like `"author.name"`.

- **chrome_ext_name(manifest_path):** Resolves Chrome extension display names. Handles plain strings (returned as-is), `__MSG_<key>__` placeholders (resolved via `_locales/<locale>/messages.json` with case-insensitive key matching), and falls back to the 32-char extension ID on any failure.

- **emit_item(name, version, id):** Builds one catalog line applying all 7 FMT-01 degradation rules and appends to the `_section_lines` global array. When name is empty but id is known, uses id as name and suppresses bracket duplication.

- **flush_section():** Sorts and deduplicates `_section_lines[]` via `LC_ALL=C sort -f -u`, appends to `OUTPUT_FILE`, resets the buffer. Writes `  (none found)` when the buffer is empty.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Insert json_get, chrome_ext_name, emit_item, flush_section | d6d4815 | update-list.sh (+217 lines) |
| 2 | Run guarded self-test (ephemeral /tmp, not committed) | (no commit — ephemeral) | /tmp/gsd-phase1-test.zsh |

## Self-Test Results

All 20 assertions across 9 test groups passed:
- **A (json_get flat keys):** flat key, missing key, nonexistent file — all return correct values
- **B (json_get nested key):** `"author.name"` dotted path resolved correctly
- **C (emit_item 7 degradation cases):** all 7 FMT-01 cases produce exact expected strings; all-empty emits nothing
- **D (flush_section sort+dedupe+write):** 1Password sorts first (case-insensitive), duplicate removed, 3 lines output
- **E (flush_section empty buffer):** writes `  (none found)` 
- **F (determinism):** two consecutive runs produce byte-identical output (FMT-04 satisfied)
- **G (chrome_ext_name __MSG_ resolution):** `__MSG_extName__` → `"Bitwarden Password Manager"` via en/messages.json
- **H (chrome_ext_name plain name):** plain string returned as-is
- **I (chrome_ext_name ID fallback):** returns 32-char extension ID when messages.json absent

## Deviations from Plan

**1. [Rule 3 - Blocking] BSD sed syntax incompatibility in helper extraction**

- **Found during:** Task 2
- **Issue:** The extraction command documented in the plan (`sed -n '/^json_get()/,/^generate_catalog()/{ /^generate_catalog()/d; p }'`) uses GNU sed syntax. macOS BSD sed rejects the compound command with "extra characters at the end of p command."
- **Fix:** Replaced with `awk` using line-number-based extraction: computed exact line numbers of `json_get()` start and the comment block preceding `generate_catalog`, then used `awk "NR>=START && NR<=STOP"` to extract the helper block.
- **Files modified:** /tmp/gsd-phase1-helpers.zsh (generated in /tmp, not committed)
- **Impact:** None on update-list.sh — extraction is only used for test isolation.

**2. [Rule 3 - Blocking] `setopt err_exit` caused early test termination**

- **Found during:** Task 2 (first test run)
- **Issue:** `setopt err_exit` in the test script caused exit on the first `assert_eq` that involved a subshell returning a non-zero exit (json_get A2). The test aborted after one PASS.
- **Fix:** Removed the `setopt err_exit` line. Assertions use explicit `if/then` blocks and are immune to exit propagation from subshells.
- **Files modified:** /tmp/gsd-phase1-test.zsh only (ephemeral, not committed)
- **Impact:** None on update-list.sh.

## Known Stubs

None. The helpers are complete implementations, not placeholders.

## Threat Flags

None. Phase 1 introduces no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. `json_get` extracts exactly one field per call (no enumeration), `flush_section` writes only caller-supplied scalars that have already been extracted by the caller.

## Self-Check: PASSED

- update-list.sh exists and contains all four function definitions: FOUND
- Commit d6d4815 exists: FOUND
- zsh -n update-list.sh exits 0: VERIFIED
- All 20 self-test assertions pass: VERIFIED
