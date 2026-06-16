---
phase: 04-browser-collectors
plan: "02"
subsystem: update-list.sh
tags: [firefox, browser-extensions, collector, profiles.ini, jq, plutil, location-filter, app-profile]
dependency_graph:
  requires: [04-01-SUMMARY.md]
  provides: [collect_firefox_extensions]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [emit_item->flush_section collector, profiles.ini Path= iteration, jq tab-delimited IFS=$'\t' read, plutil index-loop fallback, location==app-profile filter, flush-after-outer-loop cross-profile dedup]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - "profiles.ini grep '^Path=' | sed 's/^Path=//' for profile discovery (relative paths, no external tool needed)"
  - "location == 'app-profile' filter via jq select() — correct and sufficient to exclude all 12 app-builtin and app-builtin-addons system extensions on this machine"
  - "IFS=$'\\t' tab-delimited jq output with while read loop — required because addon names contain spaces"
  - ".defaultLocale.name (capital L) — not defaultlocale; both jq and plutil are case-sensitive"
  - "plutil index-loop with break on non-zero exit as end-of-array sentinel"
  - "flush_section called ONCE after outer while read loop (not inside profile loop) for correct cross-profile accumulation and dedup"
  - "_section_lines=() defensive reset at top of function per Phase 1 contract (Pitfall 7)"
  - "collect_firefox_extensions NOT called from generate_catalog — Phase 5 wires this"
metrics:
  duration_seconds: 90
  completed_date: "2026-06-13"
  tasks_completed: 1
  files_modified: 1
---

# Phase 04 Plan 02: collect_firefox_extensions Summary

## One-liner

Firefox extension collector with profiles.ini Path= iteration, app-profile location filter, jq tab-delimited primary path (handles spaces in names), plutil index-loop fallback, and cross-profile dedup via flush_section producing deterministic "Firefox Extensions" section output.

## What Was Built

One new Zsh collector function inserted in `update-list.sh` after `collect_chrome_extensions` (line 1311) and before `generate_catalog` (line 1383):

| Function | Requirement | Source | Output Format |
|----------|-------------|--------|---------------|
| `collect_firefox_extensions` | FF-01 | `~/Library/Application Support/Firefox/profiles.ini` + per-profile `extensions.json` | `name (version) [id]` |

The function follows the established Phase 2/3/4 collector pattern: `write_section` → `_section_lines=()` → iterate profiles → `emit_item` per app-profile addon → `flush_section` once after outer loop.

## Task Results

### Task 1: Insert collect_firefox_extensions into update-list.sh

- **Commit:** e1d3361
- **Files:** update-list.sh (+69 lines)
- **Implementation:**
  - Profile discovery: `grep '^Path=' "$profiles_ini" | sed 's/^Path=//'` piped into `while IFS= read -r rel_path` — no external tool, handles relative paths
  - extensions.json guard: `[[ -f "$ext_json" ]] || continue` — skips profiles with no extensions.json (e.g. l7e7es5w.default on this machine)
  - jq primary path: `jq -r '.addons[] | select(.location == "app-profile") | "\(.defaultLocale.name // .id)\t\(.version // "")\t\(.id)"'` with `while IFS=$'\t' read -r name version id`
  - plutil fallback: `idx=0` loop using `plutil -extract "addons.${idx}.location"` break as array sentinel; extracts `addons.N.defaultLocale.name`, `.version`, `.id` per app-profile addon
  - Graceful degradation: `profiles.ini` absent → `echo "  NOTE: Firefox not installed."` + `flush_section`
  - `flush_section` called once after the entire outer `while read` loop for correct cross-profile dedup
  - `_section_lines=()` defensive reset immediately after `write_section "Firefox Extensions"` call
- **Expected live result:** 6 app-profile addons from default-release profile (DuckDuckGo Search & Tracker Protection, Evernote Web Clipper, Grammarly, LastPass, New Tab, Vue.js devtools); l7e7es5w.default profile skipped (no extensions.json); 12 app-builtin and app-builtin-addons correctly excluded

## Verification Results

| Check | Result |
|-------|--------|
| `zsh -n update-list.sh` | PASS |
| `collect_firefox_extensions` defined exactly once | PASS (grep count = 1) |
| `IFS=$'\t'` present in function (line 1351) | PASS |
| `.defaultLocale.name` (capital L) present in jq expression and plutil path | PASS (lines 1356, 1365) |
| `select(.location == "app-profile")` in jq expression | PASS (line 1355) |
| plutil index-loop with `while true` / `addons.${idx}.location` / break sentinel | PASS |
| `flush_section` called after outer profile loop (not inside it) | PASS (line 1379) |
| `_section_lines=()` reset present at top of function | PASS (line 1334) |
| `generate_catalog` does NOT call `collect_firefox_extensions` | PASS (only definition + comment references) |
| Both `collect_chrome_extensions` and `collect_firefox_extensions` defined | PASS (lines 1253, 1328) |
| No unexpected file deletions in commit | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The function is fully implemented with correct Firefox profile logic. No hardcoded values or placeholders.

## Threat Flags

None. `collect_firefox_extensions` reads only local filesystem extensions.json files and emits only public metadata (addon names, versions, IDs — same data visible on the Firefox Add-ons site). No new network endpoints, auth paths, or secrets handling introduced.

T-04-02 (path traversal): Mitigated — `profiles.ini` Path= values are relative paths; full path constructed as `"${ff_dir}/${rel_path}/extensions.json"` guarded by `[[ -f "$ext_json" ]] || continue` before any read; `2>/dev/null` suppresses errors on bad paths.

## Self-Check: PASSED

Files exist:
- update-list.sh: FOUND (modified with collect_firefox_extensions at line 1328)

Commits exist:
- e1d3361: verified (feat(04-02): add collect_firefox_extensions to update-list.sh)
