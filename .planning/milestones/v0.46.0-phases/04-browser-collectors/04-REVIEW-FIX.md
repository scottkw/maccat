---
phase: 04-browser-collectors
fixed_at: 2026-06-13T00:00:00Z
review_path: .planning/phases/04-browser-collectors/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-06-13
**Source review:** .planning/phases/04-browser-collectors/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-02: Chrome `ls -1` for version-dir selection includes non-version entries

**Files modified:** `update-list.sh`
**Commit:** cd16803
**Applied fix:** Inserted `| grep -E '^[0-9]'` between `ls -1 "$ext_dir"` and `sort -V | tail -1` so only version-like directory entries (starting with a digit, e.g. `1.0.0_0`, `14.1302.0_0`) are candidates. Non-version files such as `_crx_invalidation_map` can no longer be selected as `ver_dir` and silently drop a valid extension.

### IN-02: Chrome profile enumeration iterates `_metadata` directory as an extension ID

**Files modified:** `update-list.sh`
**Commit:** cd16803
**Applied fix:** Added `[[ "$ext_id" == _* ]] && continue` immediately after the `Temp` guard. This explicitly skips any extension-ID directory whose name begins with an underscore (Chrome's convention for internal directories), eliminating the unnecessary `ls`/`sort`/`[[ -f ]]` no-op on every Chrome run.

### WR-01: Firefox `profiles.ini` CRLF not stripped

**Files modified:** `update-list.sh`
**Commit:** 5981b8f
**Applied fix:** Added `| tr -d '\r'` to the `profiles.ini` extraction pipeline: `grep '^Path=' ... | sed 's/^Path=//' | tr -d '\r'`. This strips any trailing carriage-return bytes from profile path values so a Windows-CRLF-contaminated `profiles.ini` (from cross-platform sync) does not produce `rel_path` values with a stray `\r` that silently invalidates all `[[ -f "$ext_json" ]]` checks.

### IN-01: Firefox jq path emits literal `"null"` if `.id` is null in malformed JSON

**Files modified:** `update-list.sh`
**Commit:** 5981b8f
**Applied fix:** Changed the jq template to use `// ""` as the final fallback for both name and id: `"\(.defaultLocale.name // .id // "")\t...\t\(.id // "")"`. Added `|| "$id" == "null"` to the Zsh skip guard so a literal-null id is treated as empty (skipped), and `|| "$name" == "null"` to the name guard so it falls back to `$id` rather than emitting `"null"` in the catalog.

## Skipped Issues

None — all findings were fixed.

---

**Verification:**
- `zsh -n update-list.sh` exits 0 after all fixes.
- Live sanity-check: Chrome = 7 extensions (Bitwarden present, `nmmhkkegcc...` component excluded, no `__MSG_` strings); Firefox = 6 addons (Vue.js devtools present). Counts match pre-fix verified baseline from 04-RESEARCH.md.
- No `/Users/` path leaks or `"null"` strings in output.

---

_Fixed: 2026-06-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
