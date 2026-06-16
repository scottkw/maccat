---
phase: 11-computer-selection-cli
verified: 2026-06-14T00:00:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
---

# Phase 11: Computer Selection & CLI Verification Report

**Phase Goal:** Users select or create a computer from an always-shown menu (with a remembered default) or via `--computer`/alias flags, and can quit any menu cleanly
**Verified:** 2026-06-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | Interactive run shows a numbered list of existing computer folders + "Create new computer" + "Quit" (no silent auto-select) — SEL-01 | ✓ VERIFIED | pty harness: menu rendered `1) office … 2) alpha … 3) beta … 4) Create new computer … 5) Quit`. Discovery is union of catalog-bearing top-level dirs (`office`,`alpha`) + map values (`beta`); `.git`/`docs` excluded naturally. `select_computer` lines 342-411. |
| 2  | Remembered folder marked `(this machine — default)` and is the Enter-default — SEL-02 | ✓ VERIFIED | pty: host mapped to `office` → `1) office   (this machine — default)`; empty input → `Computer: office`, `PICKED:[office]`, exit 0. Lines 403-404, 418-419, 431-449. |
| 3  | A Mac with no map row has NO Enter-default and must choose explicitly — SEL-02 | ✓ VERIFIED | pty (no-map fixture): no marker on any row; prompt `Enter your choice [1-5]:` (no "Enter for the default"); empty input → `No default for this machine — please enter a number.` then re-prompt. Lines 420-421, 451. |
| 4  | "Create new computer" prompts, re-prompts on invalid, `mkdir -p`s the folder, uses it — SEL-03 | ✓ VERIFIED | pty: idx-3 create → `bad/name` rejected (`/`-rule) → re-prompt → `Good Name` accepted → `Good Name/` dir created on disk → `Computer: Good Name`, exit 0. Lines 464-480, routes through `validate_computer_name_quiet`. |
| 5  | Invalid menu input re-prompts indefinitely (does not exit 1) — SEL-04 | ✓ VERIFIED | Input loop `while true` with `ERROR: Invalid choice … Please enter 1-${quit_idx}.` + `continue`/loop; no cap. Lines 417-458. No-default empty input also re-prompts (case B). |
| 6  | Quit by number / q / quit (case-insensitive) / EOF prints `No catalog written.` and exits 0 — QUIT-01 | ✓ VERIFIED | pty: `q` → `No catalog written.`, exit 0. Case-insensitive via `${choice:l}` (line 427); EOF via `if ! read -r choice; then choice="$quit_idx"` (line 423); branch `exit 0` (line 461-463). |
| 7  | Selecting any computer upserts the hostname→folder map | ✓ VERIFIED | `upsert_machine_label` called on every non-Quit branch (line 487) and on the flag path (line 314). |
| 8  | `--computer "Name"` runs non-interactively, select-or-create, skips the menu — CLI-01 | ✓ VERIFIED | Flag short-circuit: `[[ -n "$TARGET_LOCATION" ]]` → `mkdir -p` (created `NewMachine/`) → `Computer: NewMachine (from command-line argument)` → return. Lines 312-317. parse arm lines 209-219. |
| 9  | `--personal`/`--office`/`--machine "X"` work as equivalent aliases routing to TARGET_LOCATION — CLI-02 | ✓ VERIFIED | Isolated parse tests: `--personal`→`personal`, `--office`→`office`, `--machine Foo`→`Foo`. Arms at lines 199-208, 238-250 all set `TARGET_LOCATION`. |
| 10 | Conflicting selecting-flags fail fast (exit 1) | ✓ VERIFIED | `--personal --computer X` → `ERROR: … mutually exclusive.`, rc 1. `selecting_flags_seen` counter + post-loop guard, lines 194/201/207/217/248/265-268. |
| 11 | Invalid `--computer`/alias name fails fast via the fatal validator | ✓ VERIFIED | `--computer 'a/b'` → `ERROR: computer name must not contain /, [, or ]`, rc 1. `validate_computer_name` calls at lines 215, 246. Missing value → `--computer requires a value`, rc 1. |
| 12 | Main block calls `select_computer` once (replacing legacy fns) | ✓ VERIFIED | Anchored non-comment `^select_computer$` == 1 (line 2410). `get_target_location`/`resolve_machine_label`/`_label_in_list` = 0 non-comment refs (fully removed). |
| 13 | Quit exits 0 before generate_catalog and git_commit_and_push run — QUIT-01 wiring | ✓ VERIFIED | awk: `select_computer` (2410) precedes `generate_catalog` (2432); retention/prune/commit all after. Quit `exit 0` at line 463 short-circuits before any write/commit. |
| 14 | display_usage documents `--computer` and the back-compat aliases | ✓ VERIFIED | Lines 81-92: synopsis `[--computer "Name" | --personal | --office]`; `--computer` primary; `--personal`/`--office`/`--machine` documented as aliases; `(no option) → interactive menu`. |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `update-list.sh` | `select_computer()` defined above source-guard | ✓ VERIFIED | Defined at line 308; source-guard at 2385. `zsh -n` exits 0; sources cleanly (`sourced-ok`). |
| `update-list.sh` | `parse_arguments` `--computer` arm + alias routing + conflict guard; main block calls `select_computer`; legacy fns removed | ✓ VERIFIED | `--computer)` arm line 209; conflict guard 265-268; main-block call 2410; legacy fns 0 refs. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| select_computer (create-new) | validate_computer_name_quiet | re-prompt loop | ✓ WIRED | Line 473; behaviorally confirmed (`bad/name` rejected, `Good Name` accepted). |
| select_computer | upsert_machine_label | remember chosen folder | ✓ WIRED | Lines 314 (flag), 487 (interactive). |
| parse_arguments --computer arm | validate_computer_name | fatal validation of flag value | ✓ WIRED | Lines 215, 246; `a/b` → exit 1. |
| main block | select_computer | single call before generate_catalog | ✓ WIRED | Line 2410, precedes 2432 (awk verified). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Syntax valid | `zsh -n update-list.sh` | rc 0 | ✓ PASS |
| Sources cleanly (guard fires) | `zsh -c "source …; echo sourced-ok"` | `sourced-ok` only | ✓ PASS |
| `--computer "Example Computer"` | isolated parse | `TARGET_LOCATION=[Example Computer]` | ✓ PASS |
| Mutual exclusion | `--personal --computer X` | rc 1, `mutually exclusive` | ✓ PASS |
| `--rename` conflict | `--rename --computer X` | rc 1, `--rename cannot be combined` | ✓ PASS |
| Invalid `--computer 'a/b'` | isolated parse | rc 1, `/`-rule ERROR | ✓ PASS |
| TTY guard | no flag + piped stdin | rc 1, `not a TTY` ERROR | ✓ PASS |
| Flag short-circuit mkdir | `TARGET_LOCATION=NewMachine; select_computer` | `NewMachine/` created, "from command-line argument" | ✓ PASS |
| Interactive menu + discovery (pty) | pty harness | union discovery, exclusions, ordering correct | ✓ PASS |
| Enter-default (pty) | empty input, host mapped | `Computer: office`, exit 0 | ✓ PASS |
| Quit-by-word (pty) | `q` | `No catalog written.`, exit 0 | ✓ PASS |
| Create-new invalid→valid (pty) | `3`,`bad/name`,`Good Name` | dir created, exit 0 | ✓ PASS |
| No-default re-prompt (pty) | empty input, no map row | re-prompts, no default | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SEL-01 | 11-01 | Interactive menu of existing folders + Create new + Quit | ✓ SATISFIED | Truth #1 (pty discovery) |
| SEL-02 | 11-01 | Last-used computer pre-selected; no Enter-default if unmapped | ✓ SATISFIED | Truths #2, #3 |
| SEL-03 | 11-01 | Create new prompts, creates folder, uses it | ✓ SATISFIED | Truth #4 |
| SEL-04 | 11-01 | Invalid menu/create input re-prompts, no abort | ✓ SATISFIED | Truths #5 |
| CLI-01 | 11-02 | `--computer "Name"` select-or-create, non-interactive | ✓ SATISFIED | Truth #8 |
| CLI-02 | 11-02 | `--personal`/`--office`/`--machine` aliases | ✓ SATISFIED | Truth #9 |
| QUIT-01 | 11-01, 11-02 | Every menu offers clean Quit (exit 0, no catalog/commit) | ✓ SATISFIED | Truths #6, #13 |

All 7 requirement IDs from PLAN frontmatter (SEL-01..04, CLI-01, CLI-02, QUIT-01) are accounted for and SATISFIED. REQUIREMENTS.md maps exactly these 7 IDs to Phase 11 — no orphaned requirements. (QUIT-01's rename-picker half is correctly deferred to Phase 12 per REQUIREMENTS.md and CONTEXT scope; Phase 11 delivers the selection-menu Quit.)

### Code-Review Fix Guards (WR-01 / WR-02)

| Guard | Status | Evidence |
| ----- | ------ | -------- |
| WR-01: empty-input with missing saved default → fail loudly (no silent computers[0] fallthrough) | ✓ VERIFIED | Lines 445-448: `if [[ -z "$choice" ]]; then echo "ERROR: saved default … is not in the computer list."; exit 1; fi` |
| WR-02: `--machine` no longer routes through MACHINE_LABEL | ✓ VERIFIED | Zero `MACHINE_LABEL` references in the file (declaration also removed); `--machine` arm sets `TARGET_LOCATION` (line 247). |

### Scope Verification

| Item | Status | Evidence |
| ---- | ------ | -------- |
| Legacy `get_target_location` removed | ✓ | 0 non-comment refs |
| Legacy `resolve_machine_label` removed | ✓ | 0 non-comment refs |
| Orphaned `_label_in_list` removed | ✓ | 0 non-comment refs |
| `rename_machine` untouched (Phase 12) | ✓ | 1 definition present (line 622) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | none | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers; no stubs. `return` statements are legitimate control flow. |

### Human Verification Required

None. All interactive TTY-menu behaviors were exercised via a Python `pty.fork()` harness against `mktemp -d` fixtures (the production script was never run live, per the destructive-script constraint). Discovery, default marking, Enter-default, no-default re-prompt, q-quit, create-new validate+mkdir, existing-select, the TTY guard, and the flag short-circuit were all confirmed behaviorally; QUIT/CLI/conflict-guard paths confirmed via isolated `parse_arguments` tests and source/awk wiring checks.

### Gaps Summary

No gaps. The phase goal is achieved: an always-shown computer-selection menu with dynamic discovery (union of catalog-bearing top-level dirs + map values), a remembered Enter-default (and correct no-default behavior), a validating create-new branch, indefinite re-prompt on invalid input, a clean Quit (number/q/quit/EOF → `No catalog written.`, exit 0) wired before any catalog write or commit, plus the `--computer` flag with `--personal`/`--office`/`--machine` aliases, fatal validation, and mutual-exclusion/`--rename` conflict guards. Legacy selection functions are fully removed; `rename_machine` is untouched for Phase 12. The WR-01 and WR-02 code-review fixes are present and verified.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
