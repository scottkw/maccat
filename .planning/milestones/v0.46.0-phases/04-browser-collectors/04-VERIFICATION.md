---
phase: 04-browser-collectors
verified: 2026-06-13T00:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 4: Browser Collectors — Verification Report

**Phase Goal:** A single run catalogs Chrome and Firefox extensions across every profile, with human-readable names resolved and built-in/system add-ons excluded.
**Verified:** 2026-06-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `collect_chrome_extensions` defined in update-list.sh, produces "Google Chrome Extensions" section | VERIFIED | Function at line 1253; section header written via `write_section "Google Chrome Extensions"` |
| 2 | Exactly 7 user Chrome extensions emitted in `name (version) [id]` format | VERIFIED | Live run: 7 lines counted (Bitwarden, Claude, Grammarly, LastPass, Matter, YouTube Watch Later Cleaner, YT Watch Later Assist) |
| 3 | "Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]" present; `__MSG_extName__` raw name resolved | VERIFIED | Live run: line confirmed; manifest inspection shows raw name `"__MSG_extName__"` → resolved via `chrome_ext_name` helper |
| 4 | Chrome Web Store Payments component `nmmhkkegccagdldgiimedpiccmgmieda` absent from output | VERIFIED | Live run: `grep nmmhkkegccagdldgiimedpiccmgmieda` returns empty; case denylist at lines 1283-1294 contains all 10 IDs |
| 5 | No raw `__MSG_` string in Chrome section output | VERIFIED | Live run: `grep '__MSG_'` returns empty |
| 6 | `collect_firefox_extensions` defined in update-list.sh, produces "Firefox Extensions" section with exactly 6 app-profile addons | VERIFIED | Function at line 1333; live run: 6 lines (DuckDuckGo, Evernote Web Clipper, Grammarly, LastPass, New Tab, Vue.js devtools) |
| 7 | "Vue.js devtools (7.7.7) [{5caff8cc-3d2e-4110-a88a-003cc85b3858}]" present; app-builtin/system addons excluded | VERIFIED | Live run: line confirmed; `select(.location == "app-profile")` filter at line 1360 excludes 12 system addons |
| 8 | Two consecutive runs produce byte-identical output (determinism) | VERIFIED | `diff run1 run2` exits 0; output is deterministic due to `LC_ALL=C sort -f -u` in `flush_section` |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` lines 1253-1316 | `collect_chrome_extensions` function | VERIFIED | 63 lines; setopt null_glob; 10-ID denylist; sort -V version selection; chrome_ext_name call; emit_item/flush_section pipeline |
| `update-list.sh` lines 1333-1385 | `collect_firefox_extensions` function | VERIFIED | 52 lines; profiles.ini Path= parsing; app-profile filter; jq IFS=$'\t' primary; plutil index-loop fallback; flush_section after outer loop |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collect_chrome_extensions` | `chrome_ext_name` helper | `name=$(chrome_ext_name "$manifest")` line 1308 | VERIFIED | Phase 1 helper called; resolves `__MSG_extName__` → "Bitwarden Password Manager" live |
| `collect_chrome_extensions` | `emit_item` → `flush_section` | `emit_item "$name" "$version" "$ext_id"` line 1311; `flush_section` line 1315 | VERIFIED | flush_section called once after outer loop (not inside profile/extension loop) |
| `collect_firefox_extensions` | `profiles.ini` Path= entries | `grep '^Path=' "$profiles_ini" | sed 's/^Path=//' | tr -d '\r'` line 1381 | VERIFIED | CRLF strip (WR-01 fix) present; relative path construction correct |
| `collect_firefox_extensions` | `jq` location filter | `select(.location == "app-profile")` in jq expression line 1360 | VERIFIED | Filters to user addons only; tab-delimited IFS=$'\t' handles spaces in names |
| `collect_firefox_extensions` | `emit_item` → `flush_section` | `emit_item "$name" "$version" "$id"` line 1359; `flush_section` line 1384 | VERIFIED | flush_section called once after the entire `while read` loop |
| Neither collector | `generate_catalog` | absence of call | VERIFIED | `generate_catalog` (lines 1399-1464) contains zero references to `collect_chrome_extensions` or `collect_firefox_extensions` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `collect_chrome_extensions` | `name` | `chrome_ext_name "$manifest"` → `_locales/<locale>/messages.json` | Yes — reads real filesystem manifests; Bitwarden confirmed live | FLOWING |
| `collect_chrome_extensions` | `version` | `json_get "$manifest" "version"` → manifest.json on disk | Yes — 7 real extensions with real versions | FLOWING |
| `collect_firefox_extensions` | `name`, `version`, `id` | `jq` on `extensions.json` in `~/Library/Application Support/Firefox/Profiles/*/` | Yes — 6 real addons from default-release profile | FLOWING |

---

### Behavioral Spot-Checks

Live harness: extracted function definitions (lines 1-1398) into `/tmp/funcs-only.zsh`, sourced in a child Zsh process with `OUTPUT_FILE=/tmp/browser-test-run{1,2}.txt` and `_section_lines=()` set. Both collectors called directly.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Chrome section header written | Live harness run 1 | "Google Chrome Extensions" + separator in output | PASS |
| Chrome: exactly 7 user extensions | Count non-header lines in Chrome section | 7 | PASS |
| Bitwarden with resolved name present | `grep "Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]"` | Found | PASS |
| Chrome Web Store component absent | `grep "nmmhkkegccagdldgiimedpiccmgmieda"` | Empty (absent) | PASS |
| No raw `__MSG_` in output | `grep "__MSG_"` | Empty (absent) | PASS |
| Firefox: exactly 6 app-profile addons | Count non-header lines in Firefox section | 6 | PASS |
| Vue.js devtools present | `grep "Vue.js devtools (7.7.7) [{5caff8cc-3d2e-4110-a88a-003cc85b3858}]"` | Found | PASS |
| Determinism: two runs byte-identical | `diff run1 run2` | Exit 0 (empty diff) | PASS |
| No `/Users/` path leaks in output | `grep "/Users/" output` | Empty (no leaks) | PASS |
| `zsh -n update-list.sh` | Syntax check | Exit 0 | PASS |

---

### Post-Review Fix Verification (04-REVIEW.md findings)

All four findings from the code review were applied and confirmed live in the code:

| Finding ID | Severity | Description | Fix Status | Evidence |
|------------|----------|-------------|------------|---------|
| WR-01 | Warning | Firefox `profiles.ini` CRLF not stripped — all profiles silently skipped on `\r`-contaminated ini | VERIFIED FIXED | Line 1381: `| tr -d '\r'` present in pipeline; commit 5981b8f |
| WR-02 | Warning | Chrome `ls -1` selects non-version entries (e.g. `_crx_invalidation_map`); valid extension silently skipped | VERIFIED FIXED | Line 1301: `| grep -E '^[0-9]'` present before `sort -V`; commit cd16803 |
| IN-02 | Info | Chrome `_metadata` directory iterated as extension ID (harmless no-op) | VERIFIED FIXED | Line 1280: `[[ "$ext_id" == _* ]] && continue` present; commit cd16803 |
| IN-01 | Info | Firefox jq emits literal `"null"` if `.id` is null in malformed JSON | VERIFIED FIXED | Line 1361: `.id // ""` present in jq template; line 1357: `|| "$id" == "null"` guard present; commit 5981b8f |

---

### Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|---------|
| CHR-01 | Phase 4 | Catalog Google Chrome extensions across all profiles; resolve `__MSG_*` names; fall back to extension ID | SATISFIED | `collect_chrome_extensions` fully implemented; live output shows 7 resolved names with no raw `__MSG_` strings |
| FF-01 | Phase 4 | Catalog Firefox extensions across all profiles; exclude built-in/system add-ons | SATISFIED | `collect_firefox_extensions` fully implemented; live output shows 6 `app-profile` addons; 12 system addons correctly excluded |

Both requirements are marked "Complete" in REQUIREMENTS.md traceability table.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in modified lines | — | — |

No stub patterns, hardcoded empty returns, or debt markers were found in `collect_chrome_extensions` (lines 1253-1316) or `collect_firefox_extensions` (lines 1333-1385).

---

### Human Verification Required

None. All behavioral assertions were verified programmatically via the live harness against real Chrome and Firefox data on this machine. The output is deterministic plain text with no visual/UI or external-service dependencies.

---

## Gaps Summary

No gaps. All 8 must-have truths are verified. All 4 post-review fixes are confirmed in the live code. All behavioral spot-checks pass. Both CHR-01 and FF-01 are satisfied. The phase goal — "A single run catalogs Chrome and Firefox extensions across every profile, with human-readable names resolved and built-in/system add-ons excluded" — is achieved.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
