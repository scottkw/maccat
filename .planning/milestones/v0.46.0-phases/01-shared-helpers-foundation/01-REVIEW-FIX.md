---
phase: 01-shared-helpers-foundation
fixed_at: 2026-06-13T00:00:00Z
review_path: .planning/phases/01-shared-helpers-foundation/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-06-13
**Source review:** .planning/phases/01-shared-helpers-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, WR-03 — Info findings IN-01, IN-02 excluded per fix_scope)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: `json_get` with empty key echoes the entire JSON file (FMT-03 violation)

**Files modified:** `update-list.sh`
**Commit:** `1fd23b2`
**Applied fix:** Added `[[ -n "$key" ]] || { echo ""; return; }` immediately after the file-existence guard in `json_get`. An empty key now causes the function to return an empty string immediately, before reaching the jq/plutil branch where `getpath([])` would otherwise dump the full root object.

---

### WR-01: jq branch in `json_get` lacks the `|| value=""` defensive guard present in the plutil branch

**Files modified:** `update-list.sh`
**Commit:** `1ec5742`
**Applied fix:** Appended `|| value=""` to the jq command substitution line, making both branches symmetric: `value=$(jq ...) || value=""`. The two branches now have identical defensive behavior and the function is safe if `set -e` is ever added.

---

### WR-02: `__MSG___` (zero-length key) mis-classified as a message placeholder

**Files modified:** `update-list.sh`
**Commit:** `14e1c7c`
**Applied fix:** Changed `[[ "$name" != __MSG_*__ ]]` to `[[ "$name" != __MSG_?*__ ]]`. The `?*` pattern requires at least one character between the prefix and suffix, matching Chrome's spec for `__MSG_<messageName>__`. `__MSG___` (empty key) is now treated as a plain literal name rather than triggering locale resolution. Verified in Zsh: `__MSG_extName__` still routes to locale lookup; `__MSG___` passes through as plain.

---

### WR-03: `local resolved` declared twice in `chrome_ext_name` (redundant re-declaration in same function scope)

**Files modified:** `update-list.sh`
**Commit:** `cf55088`
**Applied fix:** Added `local resolved=""` to the existing local-variable block at the top of `chrome_ext_name` and removed the two per-branch `local resolved=""` declarations (one in the jq branch, one in the plutil branch). The variable is now declared exactly once at function scope, matching Zsh semantics and eliminating the misleading suggestion that the two branches operate on independent variables.

---

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-06-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
