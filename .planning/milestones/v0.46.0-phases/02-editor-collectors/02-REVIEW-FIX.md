---
phase: 02-editor-collectors
fixed_at: 2026-06-13T16:10:00Z
review_path: .planning/phases/02-editor-collectors/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-06-13
**Source review:** `.planning/phases/02-editor-collectors/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01, WR-02, WR-03, IN-01; IN-02 excluded per scope)
- Fixed: 4
- Skipped: 0

---

## Fixed Issues

### WR-01: `jq -r` without `// ""` emits literal `"null"` string for absent/null fields in file-fallback path

**Files modified:** `update-list.sh`
**Commit:** 5182634
**Applied fix:** Added `// ""` null-coalescing to all three jq field extractions in the file-fallback `while IFS= read -r entry` loop of both `collect_vscode_extensions` (lines 617-619) and `collect_cursor_extensions` (lines 710-712). The three calls `.identifier.id // ""`, `.version // ""`, and `.relativeLocation // ""` now produce empty strings for absent/null JSON fields rather than the literal string `"null"`. The existing `[[ -z "$id" ]] && continue` guard now correctly catches null identifiers. A missing version now produces `name [id]` output (FMT-01 degraded form) rather than `name (null) [id]`.

**Sanity check:** Verified against real `~/.vscode/extensions/extensions.json` (22 extensions). Zero null contaminations. All entries produced correct `name (version) [id]` format. Missing-version degradation test produced `Test Extension [test.missing-version]` with no `(null)`.

---

### WR-02: CLI path silently drops displayName resolution when jq absent (no plutil fallback for `relativeLocation` lookup)

**Files modified:** `update-list.sh`
**Commit:** 48c4349
**Applied fix:** Restructured the `relativeLocation` lookup block in the CLI path of both collectors. The simple `if [[ -f "$ext_json" ]] && command -v jq &>/dev/null` guard was replaced with a nested `if [[ -f "$ext_json" ]]; then if command -v jq; then ... else ... fi; fi` structure. The `else` branch adds a `plutil` index-scan loop (mirroring the file-fallback path) that iterates over `extensions.json` entries by numeric index, matching on `.identifier.id`, and extracts `.relativeLocation` when found. Also added `// ""` null-coalescing to the jq `.relativeLocation` extraction in the CLI path. Safe arithmetic `scan_idx=$((scan_idx + 1))` used instead of `((scan_idx++))`. Applied to both `collect_vscode_extensions` and `collect_cursor_extensions`.

---

### WR-03: CLI path: no-`@`-separator guard missing — malformed CLI output lines produce duplicate id/version

**Files modified:** `update-list.sh`
**Commit:** da71259
**Applied fix:** Added `[[ "$id" == "$version" ]] && continue` guard immediately after the `id="${line%@*}"` / `version="${line##*@}"` split in the CLI `while IFS= read -r line` loop of both collectors. When no `@` separator is present, both parameter expansions leave the variable equal to the full original line; the guard detects this equality and skips the malformed line. Applied to both `collect_vscode_extensions` and `collect_cursor_extensions`.

---

### IN-01: Loop variable `line` not declared `local` in CLI path of both collectors

**Files modified:** `update-list.sh`
**Commit:** d048995
**Applied fix:** Added `line=""` to the existing `local` declaration line in both `collect_vscode_extensions` (line 569) and `collect_cursor_extensions` (line 659). The declarations now read: `local id="" version="" rel_loc="" pkg_json="" display_name="" cli_output="" entry="" line=""`. This satisfies the CLAUDE.md convention "Use `local` for all function-scoped variables."

---

## Skipped Issues

### IN-02: ~72 lines duplicated between the two collectors; shared helper would reduce bug-fix surface

**File:** `update-list.sh:566-638` vs `update-list.sh:656-728`
**Reason:** Excluded from fix scope per task constraints — "too large/risky for this pass." The duplication is correct and structural-only. All bug fixes (WR-01, WR-02, WR-03, IN-01) were applied symmetrically to both copies.

---

## Verification

- `zsh -n update-list.sh` exits 0 after all fixes
- Live sanity check against `~/.vscode/extensions/extensions.json` (22 real extensions):
  - 0 null contaminations
  - All extensions show real display names (e.g., "GitLens — Git supercharged", "Python", "Auto Rename Tag") not bare IDs
  - All versions present and formatted correctly
  - Missing-version degradation produces `name [id]` (no `(null)`)
- Commit log: d048995 (IN-01) → da71259 (WR-03) → 5182634 (WR-01) → 48c4349 (WR-02)

---

_Fixed: 2026-06-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
