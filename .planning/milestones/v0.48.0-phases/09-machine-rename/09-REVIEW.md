---
phase: 09-machine-rename
reviewed: 2026-06-14T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 9: Code Review Report (Iteration 2 — Re-review)

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 1
**Status:** clean (all prior BLOCKER/WARNING findings resolved; 2 non-blocking INFO carryovers remain)

## Summary

Re-review of iteration 1's 2 CRITICAL + 3 WARNING findings against `update-list.sh` after
the auto-fix pass. All five are **genuinely resolved**, verified by reading plus targeted
behavioral testing in throwaway `mktemp -d` fixtures (the real repo was never touched).
`zsh -n update-list.sh` passes. No regressions were introduced to the rename flow, candidate
enumeration, atomic map write, or staging.

Verification performed:

- **CR-01 (per-dir staging, lines 723-726):** Replaced the fatal `git add -A personal/ office/`
  with a per-directory existence-guarded loop. Behaviorally confirmed in a throwaway repo with
  `office/` absent: the personal rename now stages as a clean `R` (rename), no exit-128 abort,
  and `git diff --cached --quiet` correctly reports staged changes. The earlier map-only corrupt
  commit no longer occurs. Also confirmed `git add -A "${loc}/"` is recursive — renames in
  `personal/archive/` and `office/archive/` across both locations all stage correctly.
- **CR-02 (strict no-effect guard, line 668):** Guard is now `if (( renamed_count == 0 ))` with
  an inner `skipped_count > 0` branch. Exercised the exact conditional: `(0,0)→no-op`,
  `(0,3)→collision-only no-op (no map, no commit)`, `(2,0)` and `(2,1)→proceed`. A collision-only
  run now mutates nothing and creates no commit, satisfying the SC#5 contract.
- **WR-01 (tab-gated map rewrite, lines 696-702):** Rewrite now requires `"$line" == *$'\t'*`
  before comparing `${line#*$'\t'}` to `old_label`. Behaviorally confirmed: a real
  `realhost<TAB>OldName` line rewrites to `realhost<TAB>NewName`, while a bare no-tab line
  `OldName` (equal to old_label) is preserved verbatim and is NOT fabricated into a tab line.
- **WR-02 (push-failure guidance, lines 743-752):** The rename-path push-failure message now
  states files were ALREADY renamed on disk (with count), warns NOT to re-run `--rename` before
  resolving, and provides `git pull --rebase && git push` recovery steps. Resolved.
- **WR-03 (`--rename` + `--machine` rejected, lines 211-214):** `parse_arguments` now rejects the
  combination with a clear actionable error after the option loop. Resolved.

Regression checks (no new defects found):
- `zsh -n` clean.
- Per-dir staging loop quoting (`"${loc}/"`, `"${SCRIPT_DIR}/${loc}"`) is correct and recursive.
- Strict guard does not break genuine renames (renamed_count > 0 path still proceeds to map +
  commit).
- Tab-gated rewrite still preserves comment lines (`^#`) and blank lines verbatim, and still
  rewrites legitimate tab-delimited entries — parses correctly under `zsh`.
- Candidate enumeration (steps 2a/2b), the `${tmp%\]-*}` label-parse idiom, the atomic
  `.tmp`+`mv` map write, and the `mv "$file2" "$dest"` quoting are unchanged and intact.
- The printed `--no-commit` manual-instruction string (line 758) still shows the bare
  `git add -A personal/ office/` form, but it is human-guidance `echo` text — never executed —
  so it is acceptable per the review scope. Not flagged.

## Info

### IN-01: Duplicated candidate-enumeration and label-parse logic (carryover)

**File:** `update-list.sh:531-547` (and `resolve_machine_label` lines 444-460); label-parse idiom
`${tmp#*\[}` / `${tmp%\]-*}` repeated at lines 561-563, 640-641, 807, 825.
**Issue:** The "read distinct labels from machine-labels.tsv with O(n) dedup loop" block is
copy-pasted between `rename_machine` (2a) and `resolve_machine_label` (step 4), and the
filename `[segment]` parse idiom now has 4+ call sites. Per the project's "3 real examples
before abstracting" rule, this is a fair candidate for `parse_label_from_filename()` /
`collect_distinct_labels()` helpers. Not a correctness issue; carried over from iteration 1.
**Fix:** Optionally extract small helpers to single-source the parse idiom.

### IN-02: Redundant `cd "$SCRIPT_DIR"` in the AUTO_COMMIT branch (carryover)

**File:** `update-list.sh:710`
**Issue:** `rename_machine` runs after `git_pull` (main block line 2287-2288), which already
`cd`s to `SCRIPT_DIR`, so the `cd` at line 710 is redundant in the normal flow. Harmless and
defensible as defensive coding (the function still works if invoked independently).
**Fix:** No change required; noted for awareness.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 2)_
