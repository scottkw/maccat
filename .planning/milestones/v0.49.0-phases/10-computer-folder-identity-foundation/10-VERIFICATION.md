---
phase: 10-computer-folder-identity-foundation
verified: 2026-06-14T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 10: Computer-Folder Identity Foundation Verification Report

**Phase Goal:** The folder name is the machine identity — every new catalog is named after its folder, and the hostname→computer map records which folder this Mac uses.
**Verified:** 2026-06-14
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A catalog saved into folder `Example Computer` is named `mac-software-list-[Example Computer]-TS.txt` (no raw hostname) | VERIFIED | Line 2390: `CURRENT_MACHINE="$TARGET_LOCATION"`; line 2391: `OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"` — folder name flows directly into filename |
| 2 | Names with `/`, `[`, `]`, tab, newline, or leading/trailing whitespace are rejected; spaces/apostrophes/letters/digits/`-_.` accepted | VERIFIED | Lines 118–176: both `validate_computer_name` and `validate_computer_name_quiet` implement all four checks; isolated tests confirm: empty→exit 1, `bad[name`→exit 1, `bad/name`→return 1, ` leading`→return 1, `Example Computer`→return 0 |
| 3 | Validation rule is a single shared implementation — `validate_computer_name` (fatal/exit 1) and `validate_computer_name_quiet` (non-fatal/return 1); zero stale `validate_machine_label` refs in executable code; 3 call sites updated | VERIFIED | No `validate_machine_label` in executable lines (grep count=0). Call sites: line 226 (`parse_arguments`), line 556 (`resolve_machine_label` create-new path), line 684 (`rename_machine`). Both function bodies at lines 118–142 and 157–176 share identical 4-check logic. |
| 4 | After selecting computer X, `machine-labels.tsv` maps hostname→X (`upsert_machine_label` writes `TARGET_LOCATION`); map header says hostname→computer-folder | VERIFIED | Lines 372–418: `upsert_machine_label` reads `TARGET_LOCATION` global at both replace (line 403) and append (line 413) paths; line 417 echoes "Saved computer folder mapping". Header template lines 380–381: "hostname to computer-folder map" / "Format: hostname\tcomputer-folder". Live `machine-labels.tsv`: 2 lines contain "computer-folder". Isolated test confirmed `Example Computer` round-trips correctly into TSV. |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | `validate_computer_name` (fatal) and `validate_computer_name_quiet` (non-fatal) | VERIFIED | Both functions at lines 118–176; `zsh -n` passes |
| `update-list.sh` | `CURRENT_MACHINE="$TARGET_LOCATION"` feeding `OUTPUT_FILENAME` | VERIFIED | Line 2390 confirmed; no `CURRENT_MACHINE="$MACHINE_LABEL"` in executable code |
| `update-list.sh` | `upsert_machine_label` records `TARGET_LOCATION` as TSV value | VERIFIED | Lines 403, 413 write `TARGET_LOCATION`; doc comment updated at lines 361–367 |
| `update-list.sh` | Source-guard before main block | VERIFIED | Line 2354: `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`; sourcing prints only "sourced-ok" |
| `machine-labels.tsv` | Header says "hostname to computer-folder map" / "Format: hostname\tcomputer-folder" | VERIFIED | Lines 1–2 of file confirmed; 2 "computer-folder" occurrences |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `parse_arguments` (--machine flag path) | `validate_computer_name` | direct call line 226 | WIRED | Old `validate_machine_label` gone from executable code |
| `resolve_machine_label` (create-new path) | `validate_computer_name_quiet` | direct call line 556 | WIRED | Re-prompt loop preserved |
| `rename_machine` (new-label prompt) | `validate_computer_name_quiet` | direct call line 684 | WIRED | Re-prompt loop preserved |
| main block | `OUTPUT_FILENAME` | `CURRENT_MACHINE="$TARGET_LOCATION"` at line 2390 | WIRED | Folder name flows through to filename |
| `upsert_machine_label` | `machine-labels.tsv` | writes `TARGET_LOCATION` at lines 403, 413 | WIRED | Atomic tmp-file write; header updated |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Syntax valid | `zsh -n update-list.sh` | exit 0 | PASS |
| Source-guard blocks main block | `zsh -c "source update-list.sh; echo sourced-ok"` | `sourced-ok` only | PASS |
| `validate_computer_name` fatal on empty | isolated source test | `exit=1 ERROR: computer name must not be empty` | PASS |
| `validate_computer_name` fatal on `[` | isolated source test | `exit=1 ERROR: computer name must not contain /, [, or ]` | PASS |
| `validate_computer_name_quiet` passes apostrophe+spaces | isolated source test | `return 0` | PASS |
| `validate_computer_name_quiet` non-fatal on `/` | isolated source test | `rc=1 msg=ERROR: ...` shell did not exit | PASS |
| `validate_computer_name_quiet` rejects leading whitespace | isolated source test | `PASS` (return 1) | PASS |
| `upsert_machine_label` writes `TARGET_LOCATION` | isolated source test, `TARGET_LOCATION=personal` | TSV data line: `computer-two.local\tpersonal` | PASS |
| `upsert_machine_label` round-trips `Example Computer` | isolated source test | grep count=1 in TSV | PASS |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| CID-01 | New catalog named `mac-software-list-[X]-TS.txt` where X equals folder name, not raw hostname | SATISFIED | `CURRENT_MACHINE="$TARGET_LOCATION"` → `OUTPUT_FILENAME` (lines 2390–2391) |
| CID-02 | Computer name validated: rejects `/[]\t\n` and leading/trailing whitespace; allows spaces/apostrophes/letters/digits/`-_.` | SATISFIED | `validate_computer_name` / `validate_computer_name_quiet` lines 118–176; all test cases pass |
| CID-03 | `machine-labels.tsv` maps hostname→computer-folder; script records/updates on each run | SATISFIED | `upsert_machine_label` reads `TARGET_LOCATION` (lines 403, 413); called from `resolve_machine_label` (lines 442, 569); header updated |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TBD/FIXME/XXX debt markers found in modified files. No stubs, no placeholder returns, no hardcoded empty values in the modified functions.

---

## Preserved Quick-Fix Behaviors (No Regression)

All behaviors confirmed intact by grep:

- `while true` re-prompt loops: **10 loops** present (count=10) — unchanged
- Hostname-first "keep current" menu in `resolve_machine_label`: line 526 `"1) ${labels[1]}   (keep current machine name)"` — present
- Empty-Enter default in `resolve_machine_label`: preserved (not part of Phase 10 changes)
- Pure-zsh `${base##*-}` timestamp parse in `rename_machine`: line 725 `local ts="${base##*-}"` — present

---

## Deferred Items (By Design — Phase 11)

Per `10-REVIEW-FIX.md`, the following are intentionally deferred and are NOT gaps for Phase 10:

| Item | Issue | Addressed In |
|------|-------|-------------|
| WR-01 | `--machine` flag and interactive label menu accepted but ignored (filename/TSV use folder) | Phase 11 |
| WR-02 | Non-interactive fresh-host runs `exit 1` at label TTY guard | Phase 11 |
| IN-01 | Dead `MACHINE_LABEL` global + self-contradictory comment | Phase 11 |
| IN-02 | `--machine` help text inconsistency | Phase 11 |
| IN-03 | Stale `resolve_machine_label` doc header | Phase 11 |

These are observable in the code (`MACHINE_LABEL` global at line 51, `resolve_machine_label` setting `MACHINE_LABEL` at lines 562/565/568) and are NOT treated as Phase 10 gaps because Phase 11 explicitly replaces the entire label path with `select_computer`.

---

## Human Verification Required

None. All must-haves are verifiable via code reading and isolated function tests.

---

## Gaps Summary

No gaps. All 4 must-haves verified. Phase goal achieved.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
