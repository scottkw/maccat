---
phase: 01-shared-helpers-foundation
verified: 2026-06-13T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 1: Shared Helpers Foundation Verification Report

**Phase Goal:** A reusable, dependency-free helper layer exists that every later collector uses to read JSON, resolve Chrome names, emit a uniform item line, and produce stably-sorted output.
**Verified:** 2026-06-13
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `json_get` returns correct scalar via jq/plutil, returns empty string (not abort) on miss, and returns empty for empty key (CR-01 fix) | VERIFIED | Live test: flat key, nested key, missing key, nonexistent file, empty key — all 5 cases pass. Guard `[[ -n "$key" ]] \|\| { echo ""; return; }` at line 286 confirmed in code. |
| 2 | `chrome_ext_name` resolves `__MSG_*__` via `_locales/<locale>/messages.json` (case-insensitive), falls back to 32-char ID, never emits blank | VERIFIED | Live test: `__MSG_extName__` → `"Bitwarden Password Manager"` (Test G); plain name returned as-is (Test H); ID fallback when messages.json absent (Test I); `__MSG___` zero-length key treated as plain literal not placeholder (WR-02 fix, Test J). |
| 3 | `emit_item` produces correct line under all 7 FMT-01 degradation cases; never emits `id [id]` | VERIFIED | Live test: all 7 cases produce exact expected strings; all-empty emits nothing; array has 6 elements after 7 calls. |
| 4 | `flush_section` sorts via `LC_ALL=C sort -f -u`, deduplicates, resets buffer, writes "(none found)" when empty | VERIFIED | Live test: 4 inputs (1 duplicate) → 3 sorted lines (Test D); empty buffer → "  (none found)" (Test E); `_section_lines` reset to 0 after flush confirmed. |
| 5 | Two consecutive runs on unchanged input produce byte-identical output (FMT-04 determinism) | VERIFIED | Live test diff /tmp/gsd-run1.txt vs /tmp/gsd-run2.txt — empty diff (Test F). |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | Contains `json_get()`, `chrome_ext_name()`, `emit_item()`, `flush_section()` | VERIFIED | All four function definitions present at lines 278, 327, 422, 469 respectively. |
| `update-list.sh` | Helpers inserted after `write_section` (line 257), before `generate_catalog` (line 490) | VERIFIED | `write_section` at 254, `json_get` at 278, `chrome_ext_name` at 327, `emit_item` at 422, `flush_section` at 469, `generate_catalog` at 490. Order is correct. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `emit_item` | `_section_lines` | `_section_lines+=("$line")` | VERIFIED | Line 448: `_section_lines+=("$line")` — array append confirmed in code and live test. |
| `flush_section` | `OUTPUT_FILE` | `printf ... \| LC_ALL=C sort -f -u >> "$OUTPUT_FILE"` | VERIFIED | Line 473: `printf "%s\n" "${_section_lines[@]}" \| LC_ALL=C sort -f -u >> "$OUTPUT_FILE"` — exact spec match. |
| `json_get` | `plutil` | `plutil -extract "$key" raw -o - "$file" 2>/dev/null` | VERIFIED | Line 296: plutil branch confirmed present as terminal fallback. No python3 in chain (comment at line 275 explicitly excludes it). |
| `chrome_ext_name` | `json_get` | `json_get "$manifest" "name"` | VERIFIED | Line 339: `name=$(json_get "$manifest" "name")` — confirmed. |

### Data-Flow Trace (Level 4)

Not applicable. These are utility helpers — they do not render dynamic data from a store or API. They are pure functions (input args → stdout / array append) with no disconnected data path risk.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `json_get` flat key | `json_get /tmp/gsd-test-manifest.json "name"` → `"Test Extension"` | PASS | PASS |
| `json_get` empty key returns `""` (CR-01) | `json_get /tmp/gsd-test-manifest.json ""` → `""` | PASS | PASS |
| `json_get` nested key | `json_get /tmp/gsd-test-nested.json "author.name"` → `"Alice"` | PASS | PASS |
| `emit_item` 7 degradation cases | 7 calls, 6 lines in array, exact strings verified | 6/6 correct | PASS |
| `flush_section` sort+dedupe | 4 inputs (1 dup) → 3 sorted lines, first is `1Password...` | PASS | PASS |
| `flush_section` empty → "(none found)" | empty `_section_lines` → `"  (none found)"` | PASS | PASS |
| Determinism (two runs) | `diff /tmp/gsd-run1.txt /tmp/gsd-run2.txt` | empty diff | PASS |
| `chrome_ext_name` `__MSG_` resolution | `__MSG_extName__` → `"Bitwarden Password Manager"` | PASS | PASS |
| `chrome_ext_name` plain name | `"Grammarly: AI Writing Assistant"` returned as-is | PASS | PASS |
| `chrome_ext_name` ID fallback | messages.json absent → 32-char ext ID returned | PASS | PASS |
| `chrome_ext_name` WR-02 fix | `__MSG___` (zero-length key) treated as plain literal | PASS | PASS |
| `zsh -n update-list.sh` | Syntax check | exits 0 | PASS |

**23/23 spot-check assertions pass.**

### Probe Execution

No probes declared. Step 7c skipped — no `scripts/*/tests/probe-*.sh` files exist for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FMT-01 | 01-01-PLAN.md | Every new catalog item in uniform line format `name (version) [id]`, degrading gracefully | SATISFIED | `emit_item` implements all 7 cases; live tests confirm exact strings. |
| FMT-04 | 01-01-PLAN.md | Catalog output deterministic — sorted stably, two consecutive runs produce empty diff | SATISFIED | `flush_section` uses `LC_ALL=C sort -f -u`; two-run diff test confirmed empty. |

Both requirements assigned to Phase 1 in REQUIREMENTS.md traceability table are satisfied. No orphaned requirements for Phase 1.

### Code Review Findings — Confirmed Resolved

All 4 in-scope findings from 01-REVIEW.md are confirmed fixed in the live codebase:

| Finding | Severity | Fix | Verified |
|---------|----------|-----|---------|
| CR-01: empty key dumps full JSON via `getpath([])` | BLOCKER | Guard `[[ -n "$key" ]] \|\| { echo ""; return; }` at line 286 | VERIFIED — live test confirmed empty string returned for empty key |
| WR-01: jq branch lacks `\|\| value=""` defensive guard | WARNING | `value=$(jq ...) \|\| value=""` at line 291 | VERIFIED — grep confirmed `\|\| value=""` on jq assignment |
| WR-02: `__MSG___` zero-length key mis-classified as placeholder | WARNING | Pattern changed from `__MSG_*__` to `__MSG_?*__` at line 343 | VERIFIED — live test: `__MSG___` returns literal string, not ID fallback |
| WR-03: `local resolved` declared twice in `chrome_ext_name` | WARNING | Single declaration at line 334 (function top), removed from both if/else branches | VERIFIED — `sed -n '327,393p'` shows 1 `local resolved` at function top, 0 in branches |

Info findings IN-01 (`echo` vs `printf` in `flush_section` empty path) and IN-02 (redundant `command -v jq` probe) were out of scope for the fix pass per REVIEW-FIX.md. Neither constitutes a blocker for phase goal achievement.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `update-list.sh` | 471 | `echo "  (none found)"` while rest of `flush_section` uses `printf` | INFO | Cosmetic inconsistency only; functionally equivalent in Zsh. No behavior impact. Tracked as IN-01 in 01-REVIEW.md, out-of-scope for fix. |

No `TBD`, `FIXME`, or `XXX` debt markers found in the helper block (lines 259–476). No stub implementations. No hardcoded empty data passed to rendering paths. No placeholder returns.

Debt marker gate: PASSED — zero unreferenced debt markers.

### Human Verification Required

None. All phase-1 truths are mechanically verifiable (function existence, return values, sort output, buffer behavior). No visual UI, real-time behavior, or external service integration involved.

---

## Gaps Summary

No gaps. All 5 must-have truths verified, all artifacts present and substantive, all key links confirmed wired, all code review blockers confirmed resolved in live code, both requirements (FMT-01, FMT-04) satisfied.

The single spot-check failure during verification was a false positive in the test script's awk boundary pattern for WR-03 — the grep check `grep -n 'local resolved' update-list.sh` unambiguously confirms one declaration at line 334 (function top), zero inside if/else branches, exactly as specified by the WR-03 fix.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
