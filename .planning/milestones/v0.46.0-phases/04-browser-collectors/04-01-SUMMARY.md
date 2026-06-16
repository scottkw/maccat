---
phase: 04-browser-collectors
plan: "01"
subsystem: update-list.sh
tags: [chrome, browser-extensions, collector, denylist, sort-V, null_glob]
dependency_graph:
  requires: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
  provides: [collect_chrome_extensions]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [emit_item->flush_section collector, null_glob guard, sort -V version selection, case-statement denylist, chrome_ext_name name resolution]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - "sort -V for Chrome version dir selection (not lexical sort) — correct for numeric version components like 14.1302.0_0 vs 3.8_0"
  - "10-ID component denylist via case statement (no associative array needed for short fixed list)"
  - "setopt local_options null_glob set once at top of function — covers all glob expansions including Profile */"
  - "flush_section called once after outer profile loop (not inside profile loop) for cross-profile dedup"
  - "collect_chrome_extensions NOT called from generate_catalog — Phase 5 wires this"
metrics:
  duration_seconds: 69
  completed_date: "2026-06-13"
  tasks_completed: 1
  files_modified: 1
---

# Phase 04 Plan 01: collect_chrome_extensions Summary

## One-liner

Chrome extension collector with sort -V version selection, 10-ID component denylist, chrome_ext_name __MSG_ resolution, and null_glob-guarded profile enumeration producing deterministic "Google Chrome Extensions" section output.

## What Was Built

One new Zsh collector function inserted in `update-list.sh` after `collect_gemini_mcp` (line 1195) and before `generate_catalog` (line 1325):

| Function | Requirement | Source | Output Format |
|----------|-------------|--------|---------------|
| `collect_chrome_extensions` | CHR-01 | `~/Library/Application Support/Google/Chrome/*/Extensions/` | `name (version) [id]` |

The function follows the established Phase 2/3 collector pattern: `write_section` → `_section_lines=()` → enumerate → `emit_item` → `flush_section`.

## Task Results

### Task 1: Insert collect_chrome_extensions into update-list.sh

- **Commit:** b0de505
- **Files:** update-list.sh (+73 lines)
- **Implementation:**
  - Profile enumeration: `"$chrome_base/Default"` + `"$chrome_base"/Profile\ */` with `[[ -d "${profile_dir}/Extensions" ]]` guard
  - null_glob: `setopt local_options null_glob` at top of function (covers all loops)
  - Extension iteration: `"${profile_dir}/Extensions"/*/` with `[[ -e "$ext_dir" ]] || continue` null-glob guard
  - Temp dir guard: `[[ "$ext_id" == "Temp" ]] && continue`
  - 10-ID component denylist: `case "$ext_id" in ... ) continue ;; esac`
  - Version selection: `ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | sort -V | tail -1)` with empty guard
  - Manifest guard: `[[ -f "$manifest" ]] || continue`
  - Name resolution: `name=$(chrome_ext_name "$manifest")` (Phase 1 helper handles __MSG_* and fallback to ID)
  - Version: `version=$(json_get "$manifest" "version")`
  - Graceful degradation: Chrome not installed → `echo "  NOTE: Google Chrome not installed."` + `flush_section`
  - `flush_section` called once after outer profile loop for correct cross-profile dedup
- **Expected live result:** 7 user extensions (Bitwarden, Claude, Grammarly, LastPass, Matter, YouTube Watch Later Cleaner, YT Watch Later Assist); nmmhkkegccagdldgiimedpiccmgmieda excluded by denylist; no raw __MSG_ strings

## Verification Results

| Check | Result |
|-------|--------|
| `zsh -n update-list.sh` | PASS |
| `collect_chrome_extensions` defined exactly once | PASS (grep count = 1) |
| `sort -V` present in function | PASS (grep count = 3, includes comment and code) |
| `nmmhkkegccagdldgiimedpiccmgmieda` in denylist | PASS (grep count = 1) |
| All 10 component IDs present | PASS (all 10 matched) |
| `setopt local_options null_glob` in function | PASS (grep count = 4) |
| `generate_catalog` does NOT call `collect_chrome_extensions` | PASS (only 2 occurrences: comment + definition) |
| Function positioned between `collect_gemini_mcp` and `generate_catalog` | PASS (lines 1253, 1325) |
| No unexpected file deletions in commit | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The function is fully implemented with live Chrome extension data. No hardcoded values or placeholders.

## Threat Flags

None. `collect_chrome_extensions` reads only local filesystem manifest files and emits only public metadata (extension names, versions, IDs — same data visible on the Chrome Web Store). No new network endpoints, auth paths, or secrets handling introduced.

## Self-Check: PASSED

Files exist:
- update-list.sh: FOUND (modified with collect_chrome_extensions)

Commits exist:
- b0de505: verified (feat(04-01): add collect_chrome_extensions to update-list.sh)
