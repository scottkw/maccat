---
phase: 12-computer-rename
verified: 2026-06-14T00:00:00Z
status: passed
score: 16/16 must-haves verified (code-level) + 4/4 live UAT flows passed (see 12-HUMAN-UAT.md)
overrides_applied: 0
human_uat: passed 2026-06-14 — all 4 destructive interactive flows run live in a disposable clone (pty-driven). One bug found & fixed during UAT: bare `local f`/`local file2` echoing var=value into the menu (commit cf171fe; affected select_computer + rename_machine).
human_verification:
  - test: "Run `./update-list.sh --rename` interactively, observe the picker"
    expected: "An alphabetical numbered menu of existing computer folders is shown, followed by a final 'Quit' entry; selecting Quit (number / q / quit) or pressing Ctrl-D prints 'Nothing renamed.' and exits 0 with nothing moved and no commit"
    why_human: "Script is DESTRUCTIVE (moves real folders + commits to real git); the TTY-guarded interactive menu can only be exercised by a real terminal. Code path verified present and wired via source/grep; live UX flow needs a human (or a disposable clone)."
  - test: "Pick a computer, enter a brand-new valid name, accept the default [Y] rewrite prompt"
    expected: "The folder is renamed (archive rides along), every catalog whose [label]==oldname in main + archive is renamed to [newname] preserving the 14-digit timestamp, the hostname->folder map repoints to the new name, and all of it lands in a SINGLE git commit 'Rename computer: ...'"
    why_human: "End-to-end rename touches the real filesystem and real git history; cannot be run in-place. The full data flow (folder move -> filename rewrite -> map update -> single commit) is verified structurally; observed real-run behavior needs human confirmation in a throwaway clone."
  - test: "Pick a computer, enter a new name, answer 'n' at the rewrite prompt"
    expected: "Folder is renamed to the new name, existing filenames keep the OLD [label], the map STILL repoints to the new name, and the change is still committed (no renamed_count==0 abort)"
    why_human: "Opt-out path is destructive (folder move + commit); behavior verified in code but the live opt-out + still-commits outcome needs human confirmation."
  - test: "Pick computer A, enter the name of an already-existing computer B (refuse-clobber)"
    expected: "Prints 'ERROR: A computer named ... already exists. Refusing to merge. Nothing renamed.' and exits 1 with NO folder moved and NO commit"
    why_human: "Guard logic and exit 1 verified in source; the live refuse-clobber outcome on real folders needs human confirmation."
---

# Phase 12: Computer Rename Verification Report

**Phase Goal:** Users can rename a computer (folder) with all its catalog files updated to match, in a single git commit
**Verified:** 2026-06-14
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

The full `rename_machine` function (update-list.sh lines 635-918) is implemented end-to-end and matches every must-have from both PLAN frontmatters and all three divergence/code-review constraints. Every truth is verified at the code level (exists + substantive + wired + data-flow). Because the script is DESTRUCTIVE (moves real folders, rewrites real filenames, commits to real git) the live interactive TTY-menu flows cannot be run in-place; per the testing constraint these are routed to `human_needed` rather than FAILED — the implementing code for each is confirmed present and wired.

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | `--rename` shows an alphabetical numbered menu of discovered computer folders + Quit | ✓ VERIFIED | Folder-discovery union (catalog dirs `${SCRIPT_DIR}/*(/N)` + map values, deduped via `_name_in_list`) lines 647-679; alphabetical sort `${(@o)computers}` line 682; numbered menu + `quit_idx` Quit line 692-701 |
| 2  | Quit (number / q / quit / EOF) exits 0, nothing moved, no commit | ✓ VERIFIED | EOF→`quit_idx` line 707-709; `q`/`quit` lowercase match 710-713; `(( choice == quit_idx ))` → `echo "Nothing renamed."; exit 0` lines 720-723 (before any mv/commit) |
| 3  | Empty list warns "No computers found. Nothing to rename." and exits 0 | ✓ VERIFIED | Lines 684-688 |
| 4  | New-name prompt is validated and re-prompts on invalid input; EOF = clean exit 0 | ✓ VERIFIED | `validate_computer_name_quiet` re-prompt loop lines 730-741; CR-01 EOF guard `if ! read -r new_name; then echo "Nothing renamed."; exit 0` lines 732-735 |
| 5  | new==old warns and exits 0 (no move, no commit) | ✓ VERIFIED | Lines 744-747, before the mv |
| 6  | Folder-not-found warns and exits 0 (no move, no commit) | ✓ VERIFIED | `[[ ! -d "$old_dir" ]]` → warn + exit 0, lines 754-757 |
| 7  | Destination exists → HARD refuse-clobber: exit 1, no move, no commit | ✓ VERIFIED | `[[ -e "$new_dir" ]]` → ERROR + exit 1, lines 758-762; soft warning removed |
| 8  | Chosen folder moved with a single plain mv (archive rides along) before any rewrite | ✓ VERIFIED | `mv "$old_dir" "$new_dir"` line 766, FIRST, before the rewrite loop |
| 9  | Default [Y] rewrite prompt: "Rewrite all existing catalogs in 'X' to '[NewName]'? [Y/n]:" | ✓ VERIFIED | Line 779; empty/y/yes default-Y idiom lines 781-783 |
| 10 | On Y, every catalog (main + archive) with [label]==old is renamed to [new] preserving 14-digit timestamp | ✓ VERIFIED | `rewrite_dirs=("$new_dir" "${new_dir}/archive")` line 786; label-match-skip line 800; pure-zsh ts parse + `=~ ^[0-9]{14}$` lines 802-807; rename lines 808-818 |
| 11 | Rewrite skips collisions (never overwrites) and leaves non-matching labels untouched | ✓ VERIFIED | Collision-skip `[[ -e "$dest" ]]` → warn + skip lines 810-815; non-matching label `continue` line 800 |
| 12 | On n (opt-out), folder keeps new name but filenames retain old [label] | ✓ VERIFIED | Rewrite gated inside the Y branch (783-821); opt-out falls through with no rewrite; comment 822-823 |
| 13 | Map updated old→new in BOTH modes, atomically | ✓ VERIFIED | UNCONDITIONAL atomic `.tmp` + mv map rewrite lines 825-860 (after the opt-out branch); TAB-bearing value==old_name guard line 850 |
| 14 | Folder move with zero rewrites still updates map + commits (no renamed_count==0 abort) | ✓ VERIFIED | No abort gate (grep `(( renamed_count == 0 ))` = 0); commit gated on `git diff --cached --quiet` line 884, not on count |
| 15 | Folder move + filename rewrites + map update committed in a SINGLE commit | ✓ VERIFIED | `git add -A -- "${old_name}/"`, `git add -A -- "${new_name}/"`, `git add -- machine-labels.tsv` lines 881-883; one `git commit -m "Rename computer: ..."` line 889 |
| 16 | With --no-commit, manual git instructions printed instead of committing | ✓ VERIFIED | else branch lines 906-912 prints `git add -A -- '...'` + commit + push instructions; no commit attempted |

**Score:** 16/16 truths verified at code level. 4 routed to human for live destructive-flow confirmation.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `update-list.sh` (rename_machine front half) | Folder picker + Quit + new-name prompt + 4 guards + folder mv | ✓ VERIFIED | Lines 635-767; above source-guard (635 < 2428); sourceable |
| `update-list.sh` (rename_machine back half) | Opt-out rewrite + unconditional map update + single commit + --no-commit; abort gate removed | ✓ VERIFIED | Lines 769-918 |
| `test-rename-front-12-01.sh` | mktemp+PTY harness for picker/guards/move | ✓ EXISTS | Present (not re-run — PTY driver may hang non-interactively per constraint) |
| `test-rename-back-12-02.sh` | mktemp+PTY harness for rewrite/opt-out/commit | ✓ EXISTS | Present (not re-run — same constraint) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| rename_machine | validate_computer_name_quiet | re-prompt loop | ✓ WIRED | Called line 736; non-fatal validator (line 156) used, NOT the fatal `validate_computer_name` |
| rename_machine discovery | machine-labels.tsv + `${SCRIPT_DIR}/*(/N)` dirs | union dedup | ✓ WIRED | Lines 661-679 |
| map rewrite | machine-labels.tsv | atomic `.tmp` + mv, both modes | ✓ WIRED | Lines 829-858 (`: >` truncation, no NULLCMD hang) |
| git block | old/ + new/ + map staged in one commit | `git add -A --` | ✓ WIRED | Lines 881-889 |
| main block | rename_machine | `if RENAME_MODE: git_pull; rename_machine; exit 0` | ✓ WIRED | Lines 2442-2446 (untouched) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| folder move | `old_dir`/`new_dir` | derived from validated picker selection + new-name prompt | Yes — `mv` operates on real fixture dirs (verified in 12-01 harness) | ✓ FLOWING |
| filename rewrite | `file2` glob over `rewrite_dirs` | real catalog files in moved folder + archive | Yes — labels parsed from real filenames, timestamps preserved | ✓ FLOWING |
| map rewrite | `line` from `$map_file` | real machine-labels.tsv | Yes — reads + rewrites real TSV atomically | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Script syntax valid | `zsh -n update-list.sh` | exit 0 (`SYNTAX_OK`) | ✓ PASS |
| Source-guard fires (no main run on source) | `zsh -c 'source ./update-list.sh; echo ok'` | only `ok` | ✓ PASS |
| parse_arguments rejects --rename + selecting flag | `zsh -c 'source ...; parse_arguments --rename --computer X'` | ERROR `--rename cannot be combined`, rc=1 | ✓ PASS |
| No renamed_count==0 abort in rename_machine | `awk .../grep -Ec '(( renamed_count == 0 ))'` | 0 | ✓ PASS |
| No "Map not updated." text | `grep -Fc 'Map not updated.'` | 0 | ✓ PASS |
| No old_label/new_label shims in rename_machine | `awk .../grep -Ec 'old_label|new_label'` | 0 | ✓ PASS |
| No legacy personal/archive or `for loc in personal office` in rename_machine | `awk .../grep -c ...` | 0 / 0 | ✓ PASS |
| Live interactive rename flows | (destructive — cannot run) | n/a | ? SKIP → human |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| RNM-01 | 12-01 | `--rename` menu (+ Quit), accepts new name, renames folder incl. archive | ✓ SATISFIED | Truths 1-8; folder mv line 766 (archive rides along) |
| RNM-02 | 12-02 | Rewrites every catalog (main + archive) to new [name] by default; opt-out leaves filenames | ✓ SATISFIED | Truths 9-12 |
| RNM-03 | 12-02 | Updates map entries; folder move + rewrites + map in single commit (honors --no-commit); no-match/no-op warns + exits without committing | ✓ SATISFIED | Truths 5-7, 13-16 |

All three phase requirement IDs (RNM-01, RNM-02, RNM-03) are declared across the plans, present in REQUIREMENTS.md (lines 32-34), and accounted for. No orphaned requirements: REQUIREMENTS.md maps only these three IDs to Phase 12.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| update-list.sh | 910-911 | IN-01: apostrophe in folder name breaks copy-paste --no-commit instructions | ℹ️ Info | Display-only; auto-commit path unaffected. From REVIEW.md, not a blocker |
| update-list.sh | 867 | IN-02: redundant defensive `cd "$SCRIPT_DIR"` | ℹ️ Info | Harmless defensive guard |
| update-list.sh | 345-377 / 647-679 | IN-03: discovery + `_name_in_list` duplicated select_computer/rename_machine | ℹ️ Info | 2 copies — at the abstraction threshold, not over it (CLAUDE.md "3 examples" rule) |

No debt markers (TBD/FIXME/XXX), no stubs, no empty handlers, no bare `>` NULLCMD hazards. Both `upsert_machine_label` (line 573) and the rename map rewrite (line 834) use `: >`. The deferred `upsert_machine_label` bare-redirect (deferred-items.md) is RESOLVED.

### Human Verification Required

These four flows are DESTRUCTIVE (move real folders + commit to real git) and TTY-guarded, so they cannot be run in-place. The implementing code for each is verified present and wired (above). Confirm in a disposable clone:

1. **Picker + Quit/EOF** — `./update-list.sh --rename`: alphabetical menu + Quit; Quit/q/Ctrl-D → "Nothing renamed.", exit 0, nothing changed.
2. **Default-Y full rename** — pick a computer, new name, accept [Y]: folder + archive renamed, matching catalogs rewritten (timestamp preserved), map repointed, single commit "Rename computer: ...".
3. **Opt-out (n)** — folder renamed, old filenames kept, map STILL repointed, change still committed (no abort).
4. **Refuse-clobber** — entering an existing computer name → ERROR "Refusing to merge", exit 1, nothing moved/committed.

### Gaps Summary

No code-level gaps. Every must-have, both critical divergences (renamed_count==0 abort removed; HARD refuse-clobber with no soft-warning regression), and both resolved code-review findings (CR-01 EOF guard, WR-01 `--` separators — extended to git_commit_and_push normal path at lines 2391/2394) are present in update-list.sh. Phase 11 / select_computer selection behavior is untouched. The status is `human_needed` solely because the live interactive destructive flows require human confirmation in a throwaway clone per the testing constraint — not because any implementation is missing.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
